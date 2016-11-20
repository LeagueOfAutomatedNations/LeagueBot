from pyshorteners import Shortener

import leaguebot.models.map as screepmap
from leaguebot import app
from leaguebot.services import screeps, twitter, battle_description


def sendBattleMessage(battle_data):
    message = getBattleMessageText(battle_data)
    return sendToTwitter(message)


def getBattleMessageText(battle_data):
    room_name = battle_data['room']
    pvp_time = battle_data['earliest_hostilities_detected'] - 5

    history_link = getHistoryLink(room_name, pvp_time)
    return "Battle: {} - lasted {} ticks in {}. {}".format(
        " vs ".join("{}{}".format(username, " ({})".format(alliance) if alliance is not None else "")
                    for username, alliance in battle_data['alliances'].items()),
        battle_description.describe_duration(battle_data),
        battle_data['room'],
        history_link,
    )


def sendNukeMessage(nukeinfo):
    message = getNukeMessageText(nukeinfo)
    sendToTwitter(message)


def getNukeMessageText(nukeinfo):
    tick = screeps.get_time()
    eta = str(nukeinfo['landTime'] - tick)
    room_name = nukeinfo['room']
    room_owner = screepmap.getRoomOwner(room_name)
    message = 'Nuke: ' + room_name + ' in ' + str(eta) + ' ticks'

    if not room_owner:
        message += ', abandoned'
    else:
        room_alliance = screepmap.getUserAlliance(room_owner)
        message += ', defender ' + room_owner
        if room_alliance:
            message += ' (' + room_alliance + ')'

    message += ' ' + getRoomLink(room_name)
    message += ' #screeps_nuke'
    return message


def sendToTwitter(message):
    if 'SEND_TO_TWITTER' not in app.config or not app.config['SEND_TO_TWITTER']:
        return False

    try:
        message += ' #screeps_battles'
        twitter.send_twitter_message(message)
        print(message)
        return True
    except:
        return False


def getRoomLink(roomname):
    baseurl = 'https://screeps.com/a/#!/room/' + roomname
    return getShortenedLink(baseurl)


def getHistoryLink(roomname, tick):
    tick = str(int(tick) - 50)
    history_link = 'https://screeps.com/a/#!/history/' + roomname + '?t=' + tick
    return getShortenedLink(history_link)


def getShortenedLink(baseurl):
    try:
        shortener = Shortener('Isgd', timeout=3)
        url = shortener.short(baseurl)
    except:
        url = baseurl
    return url
