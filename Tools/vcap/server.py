#!/usr/bin/python
# -*- coding: utf-8 -*-

import time
import json
import os
import random
import sys

from bottle import run, post, request, response, get, route

from pgoapi import PGoApi
from pgoapi.exceptions import AuthException

sys.path.append("/RocketMap/")
from pogom.utils import generate_device_info

fn = os.path.join(os.path.dirname(__file__), 'config/config.json')
with open(fn) as json_data_file:
    config = json.load(json_data_file)

host = config['server']['host']
port = int(config['server']['port'])

hkeys = config['hash_key']
random.shuffle(hkeys)

def initApi():
    location = [float(config['location']['lat']), float(config['location']['lng'])]
    print('Using location {} for this request.'.format(str(location)))
    device_info = generate_device_info()
    api = PGoApi(device_info=device_info)

    hkey = random.choice(hkeys)
    if 'True' in hkey['enabled']:
        print('Using key {} for this request.'.format(hkey['key']))
        api.activate_hash_server(hkey['key'])

    api.set_position(*location)

    return api

def login(provider, username, password, api):
    print('Using account {} for this request.'.format(username))
    print('Using password {} for this request.'.format(password))
    print('Using provider {} for this request.'.format(provider))
    try:
        api.set_authentication(
            provider=provider,
            username=username,
            password=password)
        rv = [{'auth_status':'success'}]
    except AuthException as e:
        rv = [{'auth_status':'fail', 'error':str(e)}]
    print(rv) #DEBUG
    return dict(data=rv)

def checkChallenge(api):
    try:
        req = api.create_request()
        req.check_challenge()
        req.get_inventory()
        response = req.call()
        return response

    except Exception as e:
        print('DEBUG CC Exception: ' + str(e))
        return e

def verifyChallenge(token, api):
    try:
        response = api.verify_challenge(token=token)
        return response

    except Exception as e:
        print('DEBUG VC Exception:' + str(e))
        return e

@route('/check/<provider>/', method = 'POST')
def check(provider):
    username   = request.forms.get('username')
    password   = request.forms.get('password')

    api = initApi()

    user = login(provider, username, password, api)
    if 'success' in user['data'][0]['auth_status']:
        response = checkChallenge(api)
    else:
        rv = [{'error': str(user)}]
        return dict(data=rv)

    try:
        if 'show_challenge' in response['responses']['CHECK_CHALLENGE']:
            show_challenge = response['responses']['CHECK_CHALLENGE']['show_challenge']
            challenge_url = response['responses']['CHECK_CHALLENGE']['challenge_url']
        else:
            show_challenge = False
            challenge_url = False
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
    if 'success' in user['data'][0]['auth_status']:
        response = verifyChallenge(token, api)
    else:
        rv = [{'error': str(user)}]
        return dict(data=rv)

    try:
        if 'success' in response['responses']['VERIFY_CHALLENGE']:
            success = True
        else:
            success = False
        rv = [{'success': success}]
    except KeyError, e:
        rv = [{'error': str(e)}]

    return dict(data=rv)

run(host=host, port=port, debug=True)
