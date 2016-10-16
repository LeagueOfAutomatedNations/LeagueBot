
import click

from leaguebot import app
import leaguebot.models.battles
import leaguebot.services.alerts as alerts


@app.cli.command()
def send_slack_alerts():
    battles = leaguebot.models.battles.get_battles()
    if battles:
        for battle in reversed(battles['rooms']):
            alerts.sendBattleMessage(battle)

    nukes = leaguebot.models.battles.get_nukes()
    if nukes:
        for nuke in reversed(nukes):
            alerts.sendNukeMessage(nuke)

    click.echo('success')

