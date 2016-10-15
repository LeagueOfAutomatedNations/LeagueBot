from leaguebot.services.cache import cache
import requests

room_url = 'http://www.leagueofautomatednations.com/map/rooms.js'
alliances_url = 'http://www.leagueofautomatednations.com/alliances.js'


def getRoomOwner(room):
    room_data = getRoomData()
    if room not in room_data:
        return False
    if 'owner' not in room_data[room]:
        return False
    return room_data[room]['owner']


def getRoomLevel(room):
    room_data = getRoomData()
    if room not in room_data:
        return False
    if 'level' not in room_data[room]:
        return False
    return room_data[room]['level']


def getUserAlliance(username):
    userlist = getAllianceUserData()
    if username in userlist:
        return userlist[username]
    return False


@cache.cache(expire=60)
def getRoomData():
    r = requests.get(room_url)
    return r.json()


@cache.cache(expire=60)
def getAllianceData():
    r = requests.get(alliances_url)
    return r.json()


@cache.cache(expire=60)
def getAllianceUserData():
    alliances = getAllianceData()
    users = {}
    for alliance in alliances:
        alliance_name = alliances[alliance]['name']
        for member in alliances[alliance]['members']:
            users[member] = alliance_name
    return users
