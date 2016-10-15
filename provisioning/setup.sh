#!/usr/bin/env bash

cd /vagrant

apt-get update
apt-get -f -y install git nano man
apt-get -f -y install nginx
apt-get -f -y install python3-pip python3-dev virtualenv

virtualenv -p /usr/bin/python3 env
source env/bin/activate
pip install -r requirements.txt
mkdir /home/ubuntu/objects

export SETTINGS=/vagrant/settings
export FLASK_APP=/vagrant/leaguebot/leaguebot.py
