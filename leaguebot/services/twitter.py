import twitter
from leaguebot import app
from flask import g

def get_twitter():
    conn = getattr(g, '_twitter', None)
    if conn is None:
        g._twitter = twitter.Api(consumer_key=app.config['TWITTER_CONSUMER_KEY'],
                               consumer_secret=app.config['TWITTER_CONSUMER_SECRET'],
                               access_token_key=app.config['TWITTER_ACCESS_TOKEN_KEY'],
                               access_token_secret=app.config['TWITTER_ACCESS_TOKEN_SECRET'])
    return g._twitter


def send_twitter_message(message):
    twitter = get_twitter()
    twitter.PostUpdate(message)
