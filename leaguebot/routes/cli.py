import click

import leaguebot.models.battles
import leaguebot.services.alerts as alerts
from leaguebot import app
from leaguebot.models import history, battles, reporting

logger = app.logger


@app.cli.command()
def send_slack_alerts():
    logger.info("Checking nukes.")
    nukes = leaguebot.models.battles.get_nukes()
    if nukes:
        for nuke in reversed(nukes):
            alerts.sendNukeMessage(nuke)

    logger.info("Checking and queueing new battles")
    battles.check_and_queue_battles_once()
    logger.info("Checking each pending battle once.")
    history.process_all_pending_battles_once()
    logger.info("Reporting any finished battles.")
    reporting.report_pending_battles()
    reporting.send_slack_messages()
    reporting.send_twitter_messages()
    click.echo('success')
