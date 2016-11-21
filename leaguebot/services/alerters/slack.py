import datetime

import pytz

import leaguebot.models.map as screepmap
from leaguebot import app
from leaguebot.services import screeps, slack, battle_description


def sendBattleMessage(battle_data):
    message = getBattleMessageText(battle_data)
    return sendToSlack(message)


def getBattleMessageText(battle_data):
    room_name = battle_data['room']
    pvp_time = battle_data['earliest_hostilities_detected'] - 5

    history_link = "<https://screeps.com/a/#!/history/{0}?t={1}|{0} at {1}>".format(room_name, pvp_time)
    return "{} - {} tick battle: {} - {}{}".format(
        " vs ".join(
            "<https://screeps.com/a/#!/profile/{0}|{0}{1}>"
                .format(username, " ({})".format(alliance) if alliance is not None else "")
            for username, alliance in battle_data['alliances'].items()),
        battle_description.describe_duration(battle_data),
        battle_description.describe_creeps(battle_data),
        history_link,
        "({}, RCL {})".format(battle_data['owner'], battle_data['rcl']) if battle_data.get('rcl') else ""
    )


def sendNukeMessage(nukeinfo):
    message = getNukeMessageText(nukeinfo)
    sendToSlack(message)


def getNukeMessageText(nukeinfo):
    tick = screeps.get_time()
    eta = nukeinfo['landTime']-tick
    room_name = nukeinfo['room']
    room_owner = screepmap.getRoomOwner(room_name)
    message = str(tick) + ' - Nuke: ' + '<https://screeps.com/a/#!/room/' + room_name + '|' + room_name + '>' + ' in ' + str(eta) + ' ticks'

    eta_seconds = eta * 3
    diff = eta_seconds * 0.01
    eta_early = eta_seconds - diff
    eta_late = eta_seconds + diff

    now = datetime.datetime.utcnow().replace(tzinfo=pytz.utc)
    date_early = now + datetime.timedelta(seconds = eta_early)
    date_late = now + datetime.timedelta(seconds = eta_late)

    message += ' (between ' + date_early.strftime("%Y-%m-%d %H:%M") + ' to ' + date_late.strftime("%Y-%m-%d %H:%M %Z") + ')'

    if not room_owner:
        message += ', abandoned'
    else:
        room_alliance = screepmap.getUserAlliance(room_owner)
        message += ', defender ' + '<https://screeps.com/a/#!/profile/' + room_owner + '|' + room_owner + '>'
        if room_alliance:
            message += ' (' + room_alliance + ')'
    return message


def sendToSlack(message):
    if 'SEND_TO_SLACK' not in app.config or not app.config['SEND_TO_SLACK']:
        return False
    try:
        channel = app.config['SLACK_CHANNEL']
        success = slack.send_slack_message(channel, message)
        print(message)
        return success
    except:
        return False
