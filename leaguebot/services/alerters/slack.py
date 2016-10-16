from leaguebot import app
import leaguebot.models.map as screepmap
import leaguebot.services.screeps as screeps
import leaguebot.services.slack as slack
import re


def sendBattleMessage(battleinfo):
    message = getBattleMessageText(battleinfo)
    sendToSlack(message)


def getBattleMessageText(battleinfo):
    room_name = battleinfo['_id']
    room_owner = screepmap.getRoomOwner(room_name)
    pvp_time = str(battleinfo['lastPvpTime'])
    history_link = '<https://screeps.com/a/#!/history/' + room_name + '?t=' + pvp_time + '|' + pvp_time + '>'
    message = history_link + ' - Battle: ' + '<https://screeps.com/a/#!/room/' + room_name + '|' + room_name + '>'
    if not room_owner:
        return message

    room_level = screepmap.getRoomLevel(room_name)

    if room_level and room_level > 0:
        message += ' RCL ' + str(room_level)

    message += ', defender ' + '<https://screeps.com/a/#!/profile/' + room_owner + '|' + room_owner + '>'
    room_alliance = screepmap.getUserAlliance(room_owner)
    if room_alliance:
        message += ' (' + room_alliance + ')'

    return message


def sendNukeMessage(nukeinfo):
    message = getNukeMessageText(nukeinfo)
    sendToSlack(message)


def getNukeMessageText(nukeinfo):
    tick = screeps.get_time()
    eta = str(nukeinfo['landTime']-tick)
    room_name = nukeinfo['room']
    room_owner = screepmap.getRoomOwner(room_name)
    message = str(tick) + ' - Nuke: ' + room_name + ' in ' + str(eta) + ' ticks'

    if not room_owner:
        message += ', abandoned'
    else:
        room_alliance = screepmap.getUserAlliance(room_owner)
        message += ', defender ' + room_owner
        if room_alliance:
            message += ' (' + room_alliance + ')'
    return message


def sendToSlack(message):
    if 'SEND_TO_SLACK' not in app.config or not app.config['SEND_TO_SLACK']:
        return False
    try:
        channel = app.config['SLACK_CHANNEL']
        slack.send_slack_message(channel, message)
        print (message)
        return True
    except:
        return False
