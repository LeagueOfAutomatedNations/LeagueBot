from slackclient import SlackClient
from leaguebot import app


SLACK_TOKEN = app.config['SLACK_TOKEN']
slack_client = SlackClient(SLACK_TOKEN)

def send_slack_message(channel_id, message):
    slack_client.api_call(
        "chat.postMessage",
        channel=channel_id,
        text=message,
        username='league',
        icon_emoji=':league:'
    )
