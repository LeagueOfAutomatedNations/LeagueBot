
from leaguebot import app
import leaguebot.models.map as screepmap
import re
import leaguebot.services.db as db
import leaguebot.services.slack as slack
import leaguebot.services.screeps as screeps



def mark_sent(alert_id):
    tick = screeps.get_time()
    sql = 'REPLACE INTO ALERTS VALUES (?, ?)'
    db.runQuery(sql, (alert_id, tick))


def should_send(alert_id, limit=50):
    tick = screeps.get_time()
    limit = tick - limit
    sql = 'SELECT tick FROM ALERTS WHERE id = ?'
    row = db.find_one(sql, (alert_id,))
    if (row is not None):
        print('row found')
        if row[0] > limit:
            print('returning false')
            return False
    return True


def clean():
    tick = screeps.get_time()
    tick_limit = tick - 5000
    sql = 'DELETE FROM ALERTS WHERE tick < ?'
    db.runQuery(sql, (tick_limit,))


def sendBattleMessage(room):
    room_name = room['_id']

    if not should_send(room_name, app.config['BATTLE_RATELIMIT']):
        return False

    room_owner = screepmap.getRoomOwner(room_name)

    if not room_owner:
        sendToSlack('Battle in unowned room ' + room_name)
        mark_sent(room_name)
        return

    room_alliance = screepmap.getUserAlliance(room_owner)
    message = 'Battle in room ' + room_name + ' defended by ' + room_owner
    if room_alliance:
        message += ' of alliance ' + room_alliance

    sendToSlack(message)
    mark_sent(room_name)


def sendNukeMessage(nukeinfo):
    tick = screeps.get_time()
    eta = nukeinfo['landTime']-tick

    if eta < 10:
        sendToSlack(getNukeMessageText(nukeinfo))
        return

    if not should_send(nukeinfo['_id'], app.config['NUKE_RATELIMIT']):
        return False

    sendToSlack(getNukeMessageText(nukeinfo))
    mark_sent(nukeinfo['_id'])


def getNukeMessageText(nukeinfo):
    tick = screeps.get_time()
    eta = str(nukeinfo['landTime']-tick)
    room_name = nukeinfo['room']
    room_owner = screepmap.getRoomOwner(room_name)
    room_alliance = screepmap.getUserAlliance(room_owner)
    message = 'Nuke landing in ' + room_name + ' defended by ' + room_owner
    if room_alliance:
        message += ' of alliance ' + room_alliance
    message += ' in ' + str(eta) + ' ticks'
    return message


def sendToSlack(message):
    message = re.sub(r'([E|W][\d]+[N|S][\d]+)', addLinks, message, flags=re.IGNORECASE)
    channel = app.config['SLACK_CHANNEL']
    slack.send_slack_message(channel, message)
    print (message)


def addLinks(matchobj):
    roomname = matchobj.group(1).upper()
    return '<https://screeps.com/a/#!/room/' + roomname + '|' + roomname + '>'
