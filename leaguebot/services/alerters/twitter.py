from leaguebot import app
import leaguebot.models.map as screepmap
import leaguebot.services.screeps as screeps
import leaguebot.services.twitter as twitter
import re
from pyshorteners import Shortener


def sendBattleMessage(battleinfo):
    message = getBattleMessageText(battleinfo)
    sendToTwitter(message)


def getBattleMessageText(battleinfo):
    tick = screeps.get_time()
    room_name = battleinfo['_id']
    room_owner = screepmap.getRoomOwner(room_name)
    message = 'Battle: ' + room_name
    if room_owner:
        room_level = screepmap.getRoomLevel(room_name)
        if room_level and room_level > 0:
            message += ' RCL ' + str(room_level)
        room_alliance = screepmap.getUserAlliance(room_owner)
        message += ', defender ' + room_owner
        if room_alliance:
            message += ' (' + room_alliance + ')'

    message += ' ' + getRoomLink(room_name)
    return message


def sendNukeMessage(nukeinfo):
    message = getNukeMessageText(nukeinfo)
    sendToTwitter(message)


def getNukeMessageText(nukeinfo):
    tick = screeps.get_time()
    eta = str(nukeinfo['landTime']-tick)
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
    return message


def sendToTwitter(message):

    if 'SEND_TO_TWITTER' not in app.config or not app.config['SEND_TO_TWITTER']:
        return False

    try:
        message += ' #screeps_battles'
        twitter.send_twitter_message(message)
        print (message)
        return True
    except:
        return False


def getRoomLink(roomname):
    baseurl = 'https://screeps.com/a/#!/room/' + roomname
    try:
        shortener = Shortener('Isgd', timeout=3)
        url = shortener.short(baseurl)
    except:
        url = baseurl
    return url