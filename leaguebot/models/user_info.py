import logging

import requests
from requests.packages.urllib3.exceptions import NewConnectionError

from leaguebot.services import redis_data
from leaguebot.static_constants import ScreepsError

_URL_ROOT = "https://screeps.com/"

USERNAME_URL_FORMAT = _URL_ROOT + "api/user/find"

ALLIANCES_URL = "http://www.leagueofautomatednations.com/alliances.js"

logger = logging.getLogger("warreport")


def username_from_id(user_id):
    cached = redis_data.get_username(user_id)
    if cached is not None:
        return cached
    call_result = requests.get(USERNAME_URL_FORMAT, params={'id': user_id})
    if call_result.ok:
        name = call_result.json().get('user', {}).get('username', None)
        if name is None:
            raise ScreepsError("{} ({}, at {})".format(call_result.text, call_result.status_code, call_result.url))
        redis_data.set_username(user_id, name)
        return name
    else:
        raise ScreepsError("{} ({}, at {})".format(call_result.text, call_result.status_code,
                                                   call_result.url))


def _update_alliance_data():
    try:
        result = requests.get(ALLIANCES_URL)
    except NewConnectionError:
        logger.exception("Error getting {}.".format(ALLIANCES_URL))
        redis_data.update_alliance_data([])  # try again in 4 hours.
        return
    json_root = result.json()
    if json_root is None:
        logger.error("Error parsing alliance data as json. {} ({}, at {})"
                     .format(result.text, result.status_code, result.url))
        redis_data.update_alliance_data([])
        return

    user_alliance_tuple_list = []
    for alliance_abbrev, alliance_data in json_root.items():
        for member in alliance_data['members']:
            # TODO: do we want to use the full alliance name, or the abbreviation?
            user_alliance_tuple_list.append((member, alliance_abbrev))
    redis_data.update_alliance_data(user_alliance_tuple_list)


def alliance_from_username(username):
    # TODO: write storage methods to abstract out these database calls!
    if not redis_data.is_alliance_data_recent():
        _update_alliance_data()
    return redis_data.get_cached_alliance(username)
