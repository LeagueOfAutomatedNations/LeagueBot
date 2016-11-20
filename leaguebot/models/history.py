import asyncio

import requests
from functools import partial
from requests.packages.urllib3.exceptions import NewConnectionError

from leaguebot import app
from leaguebot.models import user_info
from leaguebot.services import redis_data, redis_queue
from leaguebot.static_constants import ScreepsError
from leaguebot.static_constants import scout, civilian, general_attacker, dismantling_attacker, healer, melee_attacker, \
    ranged_attacker, tough_attacker, work_and_carry_attacker, KEEP_IN_QUEUE_FOR_MAX_TICKS_UNSUCCESSFUL

_URL_ROOT = "https://screeps.com/"

USERNAME_URL_FORMAT = _URL_ROOT + "api/user/find"
HISTORY_URL_FORMAT = _URL_ROOT + "room-history/{room}/{tick}.json"
BATTLES_URL_FORMAT = _URL_ROOT + "api/experimental/pvp"

ALLIANCES_URL = "http://www.leagueofautomatednations.com/alliances.js"

logger = app.logger


def grab_history(room, tick):
    """
    Grabs history. TODO: use screeps-api for this.

    Currently this custom function is used instead of the screeps-api package's function in order to have custom
    handling of the 404 error case, and the case where invalid JSON is returned.

    :param room: room to grab
    :param tick: tick to grab, must be interval of 20
    :return: None if the result is an error 404, otherwise the json result output. If the URL returns 200, but has
        invalid json, a empty dummy object is returned.
    :rtype: None | dict[str, Any]
    :raises ScreepsError: if a non-OK non-404 result is returned
    """
    url = HISTORY_URL_FORMAT.format(room=room, tick=tick)
    try:
        result = requests.get(url)
    except NewConnectionError as e:
        logger.exception("NewConnectionError getting {}".format(url))
        raise ScreepsError("{} ({}, at {})".format(e, 'error', url))
    if not result.ok:
        if result.status_code == 404:
            return None
        raise ScreepsError("{} ({}, at {})".format(result.text, result.status_code, result.url))

    if not len(result.content):
        # Because of the buggy history recording system, sometimes this happens! It'll be an A-OK file return, with
        # just an empty document! It probably won't ever turn into a real document, this is the most we can expect.
        # Because of this, let's just return an empty dummy result, in order to allow the processing function to keep
        # looking at other records.
        return {'ticks': {}}

    try:
        json = result.json()
    except ValueError:
        logger.exception("Invalid JSON data from {} ({}). Ignoring, and returning an empty data set."
                         .format(result.url, result.text))
        return {'ticks': {}}

    if not json:
        raise ScreepsError("Invalid json: {} ({}, at {})".format(result.text, result.status_code, result.url))

    return json


def process_room(room_name, current_tick):
    """
    Works on room data stored in redis, returning data only when completely completed.
    :param room_name: The room name to work on
    :param current_tick: The last tick retrieved from the API (not specific to this room, just the latest known tick)
    :return: None if the room needs more processing later, otherwise a finished battle information dict
    """
    battle_data = redis_data.get_ongoing_data(room_name)
    if battle_data is None:
        logger.error("No ongoing data found for room {}! Abandoning."
                     .format(room_name))
        return {}  # this will be caught by queuing, and be removed from the queue.

    logger.debug("Started processing room {}.".format(room_name))

    changed = False
    if 'tick_to_check' in battle_data:
        logger.debug("Running initial check on room {}.".format(room_name))
        # No info has been found so far, let's do the initial check!
        tick_to_call = battle_data['tick_to_check'] - battle_data['tick_to_check'] % 20
        try:
            api_result = grab_history(room_name, tick_to_call)
        except ScreepsError:
            logger.exception("Error grabbing history")
            api_result = None  # None is already returned when the error is an expected 404 error.

        if api_result is None:
            if tick_to_call + KEEP_IN_QUEUE_FOR_MAX_TICKS_UNSUCCESSFUL < current_tick:
                logger.error("Room {} tick {} data has been unavailable for over {} ticks! Abandoning."
                             .format(room_name, tick_to_call, KEEP_IN_QUEUE_FOR_MAX_TICKS_UNSUCCESSFUL))
                return {}
            else:
                return None

        changed = True

        # First tick found! Let's modify the battle data to match this.
        battle_data['max_tick_checked'] = tick_to_call
        battle_data['player_creep_counts'] = {}
        battle_data['creeps_found'] = []
        battle_data['owner'] = None
        battle_data['rcl'] = 0
        # Since this tick to check is pretty much coming from the initial API, we're going to assume a hostile action
        # _did_ occur on this tick. If we redefine what a hostile action is in our code, _we may want to change this!_
        battle_data['earliest_hostilities_detected'] = battle_data['tick_to_check']
        battle_data['latest_hostilities_detected'] = battle_data['tick_to_check']
        battle_data['earliest_hostilities_collided'] = False
        del battle_data['tick_to_check']

        # We've found the initial history section, now let's search back as far as we can!
        # We assume that if a history earlier than the history we've already gotten is inaccessible, it will never be
        # accessible. With that assumption, it makes sense to back-search history immediately when we first find that
        # our tick's history has generated!

        # TODO: this is definitely somewhat brittle, in that if the server happens to decide to not generate the
        # 20-tick history section around when the battle was originally reported, the room will be ignored for ~2000
        # ticks!

        logger.debug("Starting search-back loop.")
        while True:
            # TODO: earliest_hostilities_collided check here!
            battle_data['max_tick_checked'] = tick_to_call
            # We process the result first in here so that we can use the result from the initial tick.
            still_a_battle = modify_data_with_history(battle_data, api_result, checking='earliest')
            if not still_a_battle:
                break
            tick_to_call -= 20  # Search 20 further back in history.
            try:
                api_result = grab_history(room_name, tick_to_call)
            except ScreepsError:
                logger.exception("Error grabbing history")
                api_result = None  # None is already returned when the error is an expected 404 error.
            if api_result is None:
                break
            logger.debug("Successfully got tick {}".format(tick_to_call))

    # At this point, we know that the initial tick has been found. Now we're just continuing to check forward.
    tick_to_call = battle_data['max_tick_checked']
    found_end = False
    logger.debug("Starting forward search loop.")
    while True:
        try:
            api_result = grab_history(room_name, tick_to_call)
        except ScreepsError:
            logger.exception("Error grabbing history")
            api_result = None  # None is already returned when the error is an expected 404 error.
        if api_result is None:
            break
        logger.debug("Successfully got tick {}".format(tick_to_call))
        still_a_battle = modify_data_with_history(battle_data, api_result, checking='latest')
        battle_data['max_tick_checked'] = tick_to_call
        changed = True
        if not still_a_battle:
            found_end = True
            battle_data['battle_still_ongoing'] = False
            break
        elif tick_to_call > battle_data['stop_checking_at']:
            found_end = True
            battle_data['battle_still_ongoing'] = True
            break
        tick_to_call += 20

    if found_end:
        logger.debug("Ended. Found end{}, submitting!"
                     .format(" (of ongoing battle)" if battle_data['battle_still_ongoing'] else ""))
        # Finished! Let's clean up the data, then return it!
        del battle_data['creeps_found']
        del battle_data['stop_checking_at']
        del battle_data['max_tick_checked']
        battle_data['duration'] = battle_data['latest_hostilities_detected'] \
                                  - battle_data['earliest_hostilities_detected'] + 1
        battle_data['alliances'] = {}
        for username in battle_data['player_creep_counts'].keys():
            battle_data['alliances'][username] = user_info.alliance_from_username(username)
        battle_data['room'] = room_name
        return battle_data
    else:
        logger.debug("Ended, but still searching!")
        if changed:
            redis_data.set_ongoing_data(room_name, battle_data)

        return None


def modify_data_with_history(battle_data, history_result, checking=None):
    """
    Modify battle data based on the specific history result.

    This will also check to see if we have frequent enough combat to warrant a continuing check.

    if 'checking' is 'earliest', than the comparison for the return value will be between the earliest hostilities
    already recorded in battle data, and either the latest hostilities found in this history result, or the first tick
    available in this history result if no hostilities are found. If the distance is longer than the peace period,
    then False is returned, indicating that the battle has ended.

    if 'checking' is 'latest', than the same thing happens, but with a comparison between the latest hostilities already
    recorded, and either the earliest hostilities in this history result, or the latest tick available in this history
    result if there are no hostilities.


    :param battle_data: The battle data to modify
    :param history_result: The history API call result.
    :param checking: `earliest` or `latest`
    :return: If checking is not None and more history should be searched, this will return true.
             If checking is not None and we've reached the end (or beginning, depending on what 'checking' is) of the
               battle, this will return False
             If checking is None, this returns None.
    """
    earliest_tick = None
    latest_tick = None
    earliest_hostilities_this_section = None
    latest_hostilities_this_section = None
    for tick, tick_data in history_result['ticks'].items():
        tick = int(tick)
        if earliest_tick is None or tick < earliest_tick:
            earliest_tick = tick
        if latest_tick is None or tick > latest_tick:
            latest_tick = tick
        hostilities_this_tick = False
        bother_finding_hostilities = earliest_hostilities_this_section is None \
                                     or latest_hostilities_this_section is None \
                                     or tick < earliest_hostilities_this_section \
                                     or tick > latest_hostilities_this_section
        for creep_id, obj_data in tick_data.items():
            # type is only set for new creeps, but we don't really care about updates to old creeps yet because
            # we're just counting raw bodyparts.
            if not obj_data:
                continue
            if obj_data.get('type') == 'creep' and creep_id not in battle_data['creeps_found']:
                battle_data['creeps_found'].append(creep_id)
                owner = obj_data['user']
                # User ID 2 is invader, user ID 3 is source keeper.
                if owner.isdigit() and (int(owner) == 2 or int(owner) == 3):
                    continue
                # TODO: maybe fetch usernames from IDs all at once later on, to ensure consistency if any user changes
                # their username while we're still scanning history?
                # Probably not too important anyways though, as our username cache lasts 5 hours.
                owner_dict = battle_data['player_creep_counts'].setdefault(user_info.username_from_id(owner), {})
                creep_type = identify_creep(obj_data)
                owner_dict[creep_type] = owner_dict.get(creep_type, 0) + 1
            if battle_data['owner'] is None and obj_data.get('type') == 'controller':
                if obj_data.get('user') is not None:
                    battle_data['owner'] = user_info.username_from_id(obj_data.get('user'))
                    battle_data['rcl'] = obj_data.get('level')
                elif obj_data.get('reservation') is not None:
                    battle_data['owner'] = user_info.username_from_id(obj_data['reservation']['user'])
                    battle_data['rcl'] = 0
            if bother_finding_hostilities and not hostilities_this_tick:
                action_log = obj_data.get('actionLog')
                if action_log and (action_log.get('attack') or action_log.get('rangedAttack')
                                   or action_log.get('rangedMassAttack')
                                   or action_log.get('heal') or action_log.get('rangedHeal')):
                    hostilities_this_tick = True

        if hostilities_this_tick:
            if earliest_hostilities_this_section is None or tick < earliest_hostilities_this_section:
                earliest_hostilities_this_section = tick
            if latest_hostilities_this_section is None or tick > latest_hostilities_this_section:
                latest_hostilities_this_section = tick
    if earliest_tick is None and latest_tick is None:
        return_value = True  # This was an empty history file! Let's just let more searching happen.
    elif checking == 'earliest':
        if latest_hostilities_this_section:
            this_sec_time = latest_hostilities_this_section
        else:
            this_sec_time = earliest_tick - 1
        # TODO: 50 here is kind of arbitrary. nhanho suggested that we could do this dynamically based on creeps -
        # that would probably work well when implemented!
        return_value = battle_data['earliest_hostilities_detected'] - this_sec_time < 50
    elif checking == 'latest':
        if earliest_hostilities_this_section:
            this_sec_time = earliest_hostilities_this_section
        else:
            this_sec_time = latest_tick + 1
        return_value = this_sec_time - battle_data['latest_hostilities_detected'] < 50
    else:
        return_value = None

    if earliest_hostilities_this_section is not None \
            and earliest_hostilities_this_section < battle_data['earliest_hostilities_detected']:
        battle_data['earliest_hostilities_detected'] = earliest_hostilities_this_section
    if latest_hostilities_this_section is not None \
            and latest_hostilities_this_section > battle_data['latest_hostilities_detected']:
        battle_data['latest_hostilities_detected'] = latest_hostilities_this_section

    return return_value


def identify_creep(creep_obj):
    body = creep_obj['body']

    def has(type):
        return any(x.get('type') == type for x in body)

    def count(type):
        return sum(x.get('type') == type for x in body)

    ranged = has('ranged_attack')
    heal = has('heal')
    attack = has('attack')
    work = has('work')
    carry = has('carry')
    claim = has('claim')
    if ranged and not attack:
        return ranged_attacker
    elif attack and not ranged:
        return melee_attacker
    elif heal and not ranged and not attack:
        return healer
    elif work and not carry and count('work') > 8:
        return dismantling_attacker
    elif (ranged or heal or attack) and not carry:
        return general_attacker
    elif all(x.get('type') == 'move' or x.get('type') == 'tough' for x in body):
        return tough_attacker
    elif (work or carry or claim) and not heal and not ranged and not attack:
        return civilian
    elif (work or carry or claim) and (heal or ranged or attack):
        return work_and_carry_attacker
    elif all(x.get('type') == 'move' for x in body):
        return scout
    else:
        # We're just saying this as info for now since we care about adding new bodytypes to the code.
        logger.info("Couldn't describe creep body: {}".format(body))
        return ''.join(x['type'][0].upper() for x in body)


def process_all_pending_battles_once():
    """
    Loops through and checks all pending battles once.
    """
    first_room = None
    while True:
        room_name = redis_queue.get_next_room_to_process(blocking=False)
        if room_name is None:
            break
        elif room_name == first_room:
            break  # We've completely cycled through the queue once.

        latest_tick = redis_data.get_latest_fetched_tick()
        if latest_tick:
            latest_tick = int(latest_tick.decode())
        else:
            latest_tick = 0

        battle_data = process_room(room_name, latest_tick)

        if battle_data is None:
            if first_room is None:
                first_room = room_name  # Mark our position in the queue so that we only loop through it once.
            continue

        logger.debug("Processed {}: submitting to reporting queue!".format(room_name))

        redis_queue.submit_processed_battle(room_name, battle_data)


@asyncio.coroutine
def continuously_processes_battles(loop):
    """

    :type loop: asyncio.events.AbstractEventLoop
    """
    while True:
        room_name = yield from loop.run_in_executor(None, partial(redis_queue.get_next_room_to_process,
                                                                  blocking=True))

        latest_tick = yield from loop.run_in_executor(None, redis_data.get_latest_fetched_tick)
        if latest_tick:
            latest_tick = int(latest_tick.decode())
        else:
            latest_tick = 0

        battle_data = yield from loop.run_in_executor(None, partial(process_room, room_name, latest_tick))

        if battle_data is None:
            # If we continue without sending queuing a finished battle, the battle will simply be sent to the back of
            # the processing queue. This way, we'll keep checking to see if we have any history parts available every 30
            # seconds, and if we have multiple battles which aren't in order, we'll still get to all of them in good
            # time.
            yield from asyncio.sleep(30, loop=loop)
            continue

        logger.debug("Processed {}: submitting to reporting queue!".format(room_name))

        yield from loop.run_in_executor(None, redis_queue.submit_processed_battle, room_name, battle_data)
