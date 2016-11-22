import datetime

import pytz

import leaguebot.models.map as screepmap
from leaguebot import app
from leaguebot.services import screeps, battle_description


def sendBattleMessage(battle_data):
    if 'SEND_TO_CLI' in app.config and app.config['SEND_TO_CLI']:
        message = getBattleMessageText(battle_data)
        app.logger.info(message)
    return True


def getBattleMessageText(battle_data):
    room_name = battle_data['room']
    pvp_time = battle_data['earliest_hostilities_detected'] - 5

    history_link = "https://screeps.com/a/#!/history/{0}?t={1}".format(room_name, pvp_time)
    return "{} - {} tick battle: {} - {}{}\n\t{}".format(
        " vs ".join("{}{}".format(username, " ({})".format(alliance) if alliance is not None else "")
                    for username, alliance in battle_data['alliances'].items()),
        battle_description.describe_duration(battle_data),
        battle_description.describe_creeps(battle_data),
        room_name,
        " (defender {}, RCL {})".format(battle_data['owner'], battle_data['rcl']) if battle_data.get('rcl') else "",
        history_link
    )


def sendNukeMessage(nukeinfo):
    if 'SEND_TO_CLI' in app.config and app.config['SEND_TO_CLI']:
        message = getNukeMessageText(nukeinfo)
        app.logger.info(message)
    return True


def getNukeMessageText(nukeinfo):
    tick = screeps.get_time()
    eta = nukeinfo['landTime'] - tick
    room_name = nukeinfo['room']
    room_owner = screepmap.getRoomOwner(room_name)
    message = str(
        tick) + ' - Nuke: ' + '<https://screeps.com/a/#!/room/' + room_name + '|' + room_name + '>' + ' in ' + str(
        eta) + ' ticks'

    eta_seconds = eta * 3
    diff = eta_seconds * 0.01
    eta_early = eta_seconds - diff
    eta_late = eta_seconds + diff

    now = datetime.datetime.utcnow().replace(tzinfo=pytz.utc)
    date_early = now + datetime.timedelta(seconds=eta_early)
    date_late = now + datetime.timedelta(seconds=eta_late)

    message += ' (between ' + date_early.strftime("%Y-%m-%d %H:%M") + ' to ' + date_late.strftime(
        "%Y-%m-%d %H:%M %Z") + ')'

    if not room_owner:
        message += ', abandoned'
    else:
        room_alliance = screepmap.getUserAlliance(room_owner)
        message += ', defender ' + '<https://screeps.com/a/#!/profile/' + room_owner + '|' + room_owner + '>'
        if room_alliance:
            message += ' (' + room_alliance + ')'
    return message
