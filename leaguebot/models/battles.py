import logging

from leaguebot.services import screeps, redis_data, redis_queue


def get_battles(since_tick=None, interval=None):
    client = screeps.get_client()
    return client.battles(sinceTick=since_tick, interval=interval)


def get_nukes():
    client = screeps.get_client()
    return client.nukes()['nukes']


def check_and_queue_battles_once():
    last_grabbed_tick = redis_data.get_latest_fetched_tick()
    if last_grabbed_tick:
        last_grabbed_tick = int(last_grabbed_tick)
    if last_grabbed_tick:
        battles = get_battles(since_tick=last_grabbed_tick)
    else:
        battles = get_battles(interval=2000)
    if not battles:
        logging.warning("Something went wrong accessing the battles API.")
        return

    new_latest_tick = int(battles['time'])

    redis_queue.push_battles_for_processing(
        new_latest_tick,
        ((obj['_id'], obj['lastPvpTime']) for obj in battles['rooms'])
    )
