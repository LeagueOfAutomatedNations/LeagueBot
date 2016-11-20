from slackclient import SlackClient

from leaguebot import app

SLACK_TOKEN = app.config['SLACK_TOKEN']
slack_client = SlackClient(SLACK_TOKEN)


def send_slack_message(channel_id, message):
    """
    Sends a slack message.
    :return: True if successful, false otherwise.
    """
    result = slack_client.api_call(
        "chat.postMessage",
        channel=channel_id,
        text=message,
        username='league',
        icon_emoji=':league:'
    )
    return 'ok' in result and not not result['ok']
