from leaguebot.services.cache import cache
import requests
import leaguebot.services.screeps as screeps


def get_battles():
    client = screeps.get_client()
    return client.battles(interval=50)


def get_nukes():
    client = screeps.get_client()
    return client.nukes()['nukes']
