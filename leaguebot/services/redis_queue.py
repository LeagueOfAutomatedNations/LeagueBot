try:
    import rapidjson as json
except ImportError:
    import json

import redis

from leaguebot import app
from leaguebot.services import redis_data
from leaguebot.static_constants import PROCESSING_QUEUE_SET, PROCESSING_QUEUE, REPORTING_QUEUE, BATTLE_DATA_EXPIRE, \
    BATTLE_DATA_KEY, KEEP_IN_QUEUE_FOR_MAX_TICKS, ROOM_LAST_BATTLE_END_TICK_KEY, ROOM_LAST_BATTLE_END_TICK_EXPIRE, \
    LAST_CHECKED_TICK_KEY, LAST_CHECKED_TICK_EXPIRE, TWITTER_QUEUE, SLACK_QUEUE

logger = app.logger

# This is a fairly rigid, fairly small little LUA script to set a single value.
# Keys should be [processing_queue_set_key, processing_queue_key, battle_info_key]
# Args should be [room_name, new_room_data_if_new_room, room_data_expire_seconds]
# This might be quite inefficient to create and pass in a new battle-data-info each call, so that could definitely
# change in the future.
# One other thing that might want to be changed about this is that the script currently runs once for each room.
# I think this _is_ better than running once on a list of rooms, which could definitely be possible, because while
# lua scripts are running the redis server pauses all other queries. However, the other way could definitely also be
# done!
_battle_insert_script = redis.client.Script(None, """
local added = redis.call('sismember', KEYS[1], ARGV[1])
if added == 0 then
    redis.call('sadd', KEYS[1], ARGV[1])
    redis.call('lpush', KEYS[2], ARGV[1])
    redis.call('set', KEYS[3], ARGV[2], 'ex', ARGV[3])
end
""")


def push_battles_for_processing(new_latest_tick, battles_array):
    """
    Pushes a number of battles into the processing queue, and sets the new latest tick (one transaction).
    :param battles_array: A list of (room_name, hostilities_tick) tuples
    """
    redis_conn = redis_data.get_connection()
    if not _battle_insert_script.sha \
            or not redis_conn.script_exists(_battle_insert_script.sha):
        # Load for pipeline
        _battle_insert_script.sha = redis_conn.script_load(_battle_insert_script.script)
    pipe = redis_conn.pipeline()

    pipe.set(LAST_CHECKED_TICK_KEY, new_latest_tick, ex=LAST_CHECKED_TICK_EXPIRE)

    for room_name, hostilities_tick in battles_array:
        _battle_insert_script(
            keys=[PROCESSING_QUEUE_SET, PROCESSING_QUEUE, BATTLE_DATA_KEY.format(room_name)],
            args=[room_name, json.dumps({
                # See storage.py for documentation on this format.
                'tick_to_check': hostilities_tick,
                'stop_checking_at': (hostilities_tick - hostilities_tick % 20) + KEEP_IN_QUEUE_FOR_MAX_TICKS,
            }), BATTLE_DATA_EXPIRE],
            client=pipe,
        )

    pipe.execute()


def get_next_room_to_process(blocking=True):
    """
    Gets a single battle to process. This method returns the battle's room, and the stored 'battle data' from the last
    time the battle was processed (or the beginning battle data if it hasn't been processed yet).
    :return: A tuple of (room_name, battle_data)
    """
    redis_conn = redis_data.get_connection()
    # TODO: This implementation currently allows for the possibility of processing the same data twice when we have at
    # least two clients, and a queue shorter than the number of clients. On one hand, this should be changed. On the
    # other, we really only support one client at a time, and this allows us to not require a separate
    # "currently_processing" queue to monitor.
    if blocking:
        return redis_conn.brpoplpush(PROCESSING_QUEUE, PROCESSING_QUEUE).decode()
    else:
        raw = redis_conn.rpoplpush(PROCESSING_QUEUE, PROCESSING_QUEUE)
        if raw is None:
            return None
        else:
            return raw.decode()


def submit_processed_battle(room_name, battle_info_dict):
    """
    Submit a processed battle via a database_key and battle_info_dict.
    :param room_name: The room name that was processed
    :param battle_info_dict: The processed battle data.
    """
    pipe = redis_data.get_connection().pipeline()
    pipe.lrem(PROCESSING_QUEUE, 0, room_name)
    pipe.srem(PROCESSING_QUEUE_SET, room_name)
    pipe.delete(BATTLE_DATA_KEY.format(room_name))
    if 'latest_hostilities_detected' in battle_info_dict:
        pipe.lpush(REPORTING_QUEUE, json.dumps(battle_info_dict))
        pipe.set(ROOM_LAST_BATTLE_END_TICK_KEY.format(room_name), battle_info_dict['latest_hostilities_detected'],
                 ex=ROOM_LAST_BATTLE_END_TICK_EXPIRE)
    else:
        # This means something has gone wrong, and no hostilities have been detected!
        # We should still remove this battle from the queue, as it was deemed 'unprocessable' by screeps_info,
        # but we shouldn't add it to the reporting queue since it wasn't processed!
        logger.debug("Battle submitted with no hostilities - not reporting battle in {}! {}".format(
            room_name, battle_info_dict))
    pipe.execute()


def get_next_battle_to_report(blocking=True):
    """
    Gets a single battle to report. This method returns the processed information dict, and a database_key for use when
    marking as completed.

    TODO: describe in detail the battle_info_dict format here.

    :return: A tuple of (battle_info_dict, database_key)
    """
    # TODO: This implementation currently allows for the possibility of processing the same data twice when we have at
    # least two clients, and a queue shorter than the number of clients. On one hand, this should be changed. On the
    # other, we really only support one client at a time, and this allows us to not require a separate
    # "currently_processing" queue to monitor.
    if blocking:
        raw_battle_info = redis_data.get_connection().brpoplpush(REPORTING_QUEUE, REPORTING_QUEUE)
    else:
        raw_battle_info = redis_data.get_connection().rpoplpush(REPORTING_QUEUE, REPORTING_QUEUE)
        if raw_battle_info is None:
            return None
    battle_info = json.loads(raw_battle_info.decode())
    return battle_info, raw_battle_info


def mark_battle_reported(database_key):
    """
    Marks a battle from the reporting queue as reported, given a database_key retrieved from get_next_battle_to_report.

    If this method isn't called, get_next_battle_to_report will start returning already-reported battles once it has
    returned each battle once.
    :param database_key: The database_key returned from get_next_battle_to_report corresponding to the battle
                         successfully reported.
    """
    redis_data.get_connection().lrem(REPORTING_QUEUE, 0, database_key)


def requeue_report(reporting_database_key, push_to_twitter, push_to_slack):
    """
    Requeues a battle from the main reporting queue into the twitter or slack queues.

    Might be just slightly overengineered, but with this format there won't ever be any repeated work and all messages
    will be reported exactly once.

    :param reporting_database_key: The database key gotten from get_next_battle_to_report - for removing from the main
            reporting queue.
    :param push_to_twitter: A single string to push to the twitter queue.
    :param push_to_slack: A single string to push to the slack queue.
    """
    pipeline = redis_data.get_connection().pipeline()
    if reporting_database_key:
        pipeline.lrem(REPORTING_QUEUE, 0, reporting_database_key)
    if push_to_twitter:
        pipeline.lpush(TWITTER_QUEUE, push_to_twitter)
    if push_to_slack:
        pipeline.lpush(SLACK_QUEUE, push_to_slack)
    pipeline.execute()


# This is a small LUA script to merge all of the items in the slack queue into one item. It's done as a LUA script
# instead of python code in order to make it a single operation.
# The first key should be the queue to merge
# The first argument should be the separator to use when merging.
# TODO: should we have a limit for how many messages we merge together / the length of the message?
_slack_merge_script = redis.client.Script(None, """
local elements = redis.call('lrange', KEYS[1], 0, -1) -- Get all elements
local merged = table.concat(elements, ARGV[1]) -- Merge
redis.call('del', KEYS[1]) -- Delete all values
redis.call('lpush', KEYS[1], merged) -- Insert the merged element
""")


def merge_slack_queue():
    """
    Merges all current messages in the slack queue into one message.
    """
    _slack_merge_script(
        keys=[SLACK_QUEUE],
        args=['\n\n'],
        client=redis_data.get_connection()
    )


def pull_reportable_message(reporting_key):
    """
    Pulls a raw string message to report
    :param reporting_key: SLACK_QUEUE or TWITTER_QUEUE
    :return: A string message
    """
    raw = redis_data.get_connection().rpoplpush(reporting_key, reporting_key)
    if raw is None:
        return None
    else:
        return raw.decode()


def finish_reportable_message(reporting_key, message):
    """
    Marks a raw string message as reported.
    :param reporting_key: SLACK_QUEUE or TWITTER_QUEUE
    :param message: The message to mark finished.
    """
    redis_data.get_connection().lrem(reporting_key, 0, message)
