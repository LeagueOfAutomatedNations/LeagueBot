from flask import Flask, render_template, request, jsonify
from leaguebot import app
from slackclient import SlackClient
import leaguebot.routes.cli
import leaguebot.routes.slashes

@app.route('/')
@app.route('/index')
def index():
    return "These are not the droids you are looking for."

