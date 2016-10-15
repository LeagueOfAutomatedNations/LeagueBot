from flask import Flask
app = Flask(__name__)
app.config.from_envvar('SETTINGS')

import leaguebot.leaguebot
