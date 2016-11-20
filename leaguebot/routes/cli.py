import asyncio

import click

import leaguebot.models.battles
import leaguebot.services.alerts as alerts
from leaguebot import app
from leaguebot.models import history, battles, reporting

logger = app.logger


@app.cli.command()
def send_slack_alerts():
    click.echo("Checking nukes.")
    nukes = leaguebot.models.battles.get_nukes()
    if nukes:
        for nuke in reversed(nukes):
            alerts.sendNukeMessage(nuke)

    click.echo("Checking and queueing new battles")
    battles.check_and_queue_battles_once()
    click.echo("Checking each pending battle once.")
    history.process_all_pending_battles_once()
    click.echo("Reporting any finished battles.")
    reporting.report_pending_battles()
    click.echo('success')


@app.cli.command()
def run_server():
    logger.debug("Started main loop.")
    loop = asyncio.get_event_loop()

    gathered_future = asyncio.gather(
        battles.check_and_queue_battles_continuously(loop),
        history.continuously_processes_battles(loop),
        reporting.reporting_loop(loop),
        loop=loop,
    )
    try:
        loop.run_until_complete(gathered_future)
    finally:
        loop.close()
