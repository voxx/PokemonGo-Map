#!/usr/bin/python
# -*- coding: utf-8 -*-

import time
import json

from bottle import run, post, request, response, get, route

from pgoapi import PGoApi
from pgoapi.exceptions import AuthException

with open('config/config.json') as json_data_file:
    config = json.load(json_data_file)

prot = config['server']['protocol']
host = config['server']['host']
port = int(config['server']['port'])

def initApi():
    location = [float(config['location']['lat']), float(config['location']['long'])]

    api = PGoApi()
    api.set_position(*location)

    return api

def login(provider, username, password, api):
    try:
        api.set_authentication(
            provider=provider,
            username=username,
            password=password)
        rv = [{'auth_status':'success'}]
    except AuthException as e:
        time.sleep(1)
        rv = [{'auth_status':'fail', 'error':str(e)}]

    return dict(data=rv)

def checkChallenge(api):
    try:
        req = api.create_request()
        response = req.check_challenge()
        response = req.get_inventory()
        response = req.call()
        return response

    except Exception as e:
        return e

def verifyChallenge(token, api):
    try:
        response = api.verify_challenge(token=token)
        return response

    except Exception as e:
        return e

@route('/check/<provider>/', method = 'POST')
def check(provider):
    username   = request.forms.get('username')
    password   = request.forms.get('password')

    api = initApi()
    user = login(provider, username, password, api)
    response = checkChallenge(api)

    try:
        show_challenge = response['responses']['CHECK_CHALLENGE']['show_challenge']
        challenge_url = response['responses']['CHECK_CHALLENGE']['challenge_url']
        rv = [{'challenge_url': challenge_url}, {'show_challenge': show_challenge}]
    except KeyError, e:
        rv = [{'error': str(e)}]

    return dict(data=rv)

@route('/verify/<provider>/', method = 'POST')
def verify(provider):
    username	= request.forms.get('username')
    password	= request.forms.get('password')
    token	= request.forms.get('token')

    api = initApi()
    user = login(provider, username, password, api)
    response = verifyChallenge(token, api)

    try:
	success = response['responses']['VERIFY_CHALLENGE']['success']
	rv = [{'success': success}]
    except KeyError, e:
        rv = [{'error': str(e)}]

    return dict(data=rv)

run(host=host, port=port, debug=True)
