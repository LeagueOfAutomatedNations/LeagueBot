import leaguebot.services.alerters.cli
import leaguebot.services.alerters.slack
import leaguebot.services.alerters.twitter
from leaguebot import app
from leaguebot.services import redis_queue
from leaguebot.static_constants import civilian, scout, SLACK_QUEUE, TWITTER_QUEUE


def should_report(battle_info):
    # Don't report a single player dismantling their own things
    #if len(battle_info['player_creep_counts']) < 2:
    #    return False

    # Don't report on short battles.
    #if 'duration' in battle_info:
    #    if battle_info['duration'] < 10:
    #        return False

    # Don't report a single civilian or scout walking into someone's owned room and being shot down
    #if not any(any(role != civilian and role != scout for role in creeps.keys())
    #           for player, creeps in battle_info['player_creep_counts'].items() if battle_info.get('owner') != player):
    #    return False
    return True


logger = app.logger


def report_pending_battles():
    """
    Tries to reports all pending battles once.
    """
    while True:
        result_tuple = redis_queue.get_next_battle_to_report(blocking=False)
        if result_tuple is None:
            break
        battle_data, database_key = result_tuple

        if not should_report(battle_data):
            logger.debug("Decided not to report battle in {}.".format(battle_data['room']))
            redis_queue.mark_battle_reported(database_key)
            continue

        if app.config.get('SEND_TO_SLACK', False):
            slack_message = leaguebot.services.alerters.slack.getBattleMessageText(battle_data)
        else:
            slack_message = None
        if app.config.get('SEND_TO_TWITTER', False):
            twitter_message = leaguebot.services.alerters.twitter.getBattleMessageText(battle_data)
        else:
            twitter_message = None
        if app.config.get('SEND_TO_CLI', False):
            # send directly since we're guaranteed success and this doesn't delay
            leaguebot.services.alerters.cli.sendBattleMessage(battle_data)

        redis_queue.requeue_report(
            database_key, twitter_message, slack_message
        )


def send_slack_messages():
    redis_queue.merge_slack_queue()
    first_failure = None  # for making sure we don't loop forever.
    while True:
        message = redis_queue.pull_reportable_message(SLACK_QUEUE)
        if message is None or message == first_failure:
            break

        success = leaguebot.services.alerters.slack.sendToSlack(message)
        if success:
            redis_queue.finish_reportable_message(SLACK_QUEUE, message)
        else:
            if first_failure is None:
                first_failure = message


def send_twitter_messages():
    first_failure = None  # for making sure we don't loop forever.
    while True:
        message = redis_queue.pull_reportable_message(TWITTER_QUEUE)
        if message is None or message == first_failure:
            break

        success = leaguebot.services.alerters.twitter.sendToTwitter(message)
        if success:
            redis_queue.finish_reportable_message(TWITTER_QUEUE, message)
        else:
            if first_failure is None:
                first_failure = message
