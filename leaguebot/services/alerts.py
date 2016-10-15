
from leaguebot import app
import leaguebot.models.map as screepmap
import re
import leaguebot.services.db as db
import leaguebot.services.slack as slack
import leaguebot.services.screeps as screeps
import leaguebot.services.twitter as twitter



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
        if row[0] > limit:
            return False
    return True


def clean():
    tick = screeps.get_time()
    tick_limit = tick - 5000
    sql = 'DELETE FROM ALERTS WHERE tick < ?'
    db.runQuery(sql, (tick_limit,))


def sendBattleMessage(battleinfo):
    room_name = battleinfo['_id']
    if not should_send(room_name, app.config['BATTLE_RATELIMIT']):
        return False

    message = getBattleMessageText(battleinfo)
    sendToSlack(message)
    sendToTwitter(message)
    mark_sent(room_name)




def sendNukeMessage(nukeinfo):
    tick = screeps.get_time()
    eta = nukeinfo['landTime']-tick
    room_owner = screepmap.getRoomOwner(nukeinfo['room'])

    if not room_owner:
        return False

    if eta < 10:
        sendToSlack(getNukeMessageText(nukeinfo))
        return

    if not should_send(nukeinfo['_id'], app.config['NUKE_RATELIMIT']):
        return False

    sendToSlack(getNukeMessageText(nukeinfo))
    sendToTwitter(getNukeMessageText(nukeinfo))
    mark_sent(nukeinfo['_id'])


def getBattleMessageText(battleinfo):
    tick = screeps.get_time()
    room_name = battleinfo['_id']
    room_owner = screepmap.getRoomOwner(room_name)
    message = str(tick) + ' - Battle: ' + room_name
    if not room_owner:
        return message

    room_alliance = screepmap.getUserAlliance(room_owner)
    message += ', defender ' + room_owner
    if room_alliance:
        message += ' (' + room_alliance + ')'

    return message


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
    message = re.sub(r'([E|W][\d]+[N|S][\d]+)', addSlackLinks, message, flags=re.IGNORECASE)
    channel = app.config['SLACK_CHANNEL']
    slack.send_slack_message(channel, message)
    print (message)

def addSlackLinks(matchobj):
    roomname = matchobj.group(1).upper()
    return '<https://screeps.com/a/#!/room/' + roomname + '|' + roomname + '>'


def sendToTwitter(message):
    message = re.sub(r'([E|W][\d]+[N|S][\d]+)', addTwitterLinks, message, flags=re.IGNORECASE)
    message += ' #screeps_battles'
    twitter.send_twitter_message(message)
    print (message)

def addTwitterLinks(matchobj):
    roomname = matchobj.group(1).upper()
    return roomname + ' (https://screeps.com/a/#!/room/' + roomname + ')'

