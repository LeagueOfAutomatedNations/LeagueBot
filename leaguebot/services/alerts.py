
from leaguebot import app
import leaguebot.models.map as screepmap
import leaguebot.services.db as db
import leaguebot.services.screeps as screeps
import leaguebot.services.alerters.twitter
import leaguebot.services.alerters.slack
import leaguebot.services.alerters.cli


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


def sendBattleMessage(battle_data):
    success = leaguebot.services.alerters.slack.sendBattleMessage(battle_data)
    success = leaguebot.services.alerters.twitter.sendBattleMessage(battle_data) and success
    success = leaguebot.services.alerters.cli.sendBattleMessage(battle_data) and success
    return success


def sendNukeMessage(nukeinfo):
    tick = screeps.get_time()
    eta = nukeinfo['landTime']-tick
    room_owner = screepmap.getRoomOwner(nukeinfo['room'])

    if not room_owner:
        return False

    if eta < 25:
        leaguebot.services.alerters.slack.sendNukeMessage(nukeinfo)
        return

    if not should_send(nukeinfo['_id'], app.config['NUKE_RATELIMIT']):
        return False

    leaguebot.services.alerters.slack.sendNukeMessage(nukeinfo)
    leaguebot.services.alerters.twitter.sendNukeMessage(nukeinfo)
    mark_sent(nukeinfo['_id'])

