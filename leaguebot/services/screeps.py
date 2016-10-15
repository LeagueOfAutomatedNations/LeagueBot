from flask import g
from leaguebot import app
from leaguebot.services.cache import cache
import screepsapi.screepsapi as screepsapi


def get_client():
    conn = getattr(g, '_screeps_client', None)
    if conn is None:
        user = app.config['API_USERNAME']
        password = app.config['API_PASSWORD']
        api = screepsapi.API(user, password)
        g._screeps_client = api
    return g._screeps_client


@cache.cache(expire=4)
def get_time():
    client = get_client()
    return client.time()
