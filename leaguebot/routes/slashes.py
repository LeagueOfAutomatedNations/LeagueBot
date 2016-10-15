from leaguebot import app
from flask import Flask, request, Response


@app.route('/slackhook')
def slackhook():

    #if not slack.verify_token(request.form.get('token')):
    #    return Response(), 400

    channel = request.form.get('channel_name')
    username = request.form.get('user_name')
    text = request.form.get('text')
    inbound_message = username + " in " + channel + " says: " + text

    return inbound_message
