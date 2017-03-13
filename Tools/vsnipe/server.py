#!/usr/bin/python
# -*- coding: utf-8 -*-

import time
import json
import os
import sys

from bottle import run, post, request, response, get, route
from base64 import b64encode

from pgoapi import PGoApi
from pgoapi.exceptions import AuthException
from pgoapi.utilities import f2i
from pgoapi import utilities as util

sys.path.append("/RocketMap/")
from pogom.utils import generate_device_info
from pogom.transform import jitter_location

fn = os.path.join(os.path.dirname(__file__), 'config/config.json')
with open(fn) as json_data_file:
    config = json.load(json_data_file)

host = config['server']['host']
port = int(config['server']['port'])
hkey = config['hash_key']['key']
accounts = config['accounts']

def initApi(lat, lng):
    location = [float(lat), float(lng)]

    device_info = generate_device_info()
    api = PGoApi(device_info=device_info)

    if 'True' in config['hash_key']['enabled']:
        print('Using key {} for this request.'.format(hkey))
        api.activate_hash_server(hkey)

    api.set_position(*location)

    return api

def login(api):
    
    username = config['accounts']['username']
    password = config['accounts']['password']
    provider = config['accounts']['provider']
    
    try:
        api.set_authentication(
            provider=provider,
            username=username,
            password=password)
        rv = [{'auth_status':'success'}]
    except AuthException as e:
        rv = [{'auth_status':'fail', 'error':str(e)}]

    return dict(data=rv)

def map_request(api, position, no_jitter=False):
    # Create scan_location to send to the api based off of position, because
    # tuples aren't mutable.
    if no_jitter:
        # Just use the original coordinates.
        scan_location = position
    else:
        # Jitter it, just a little bit.
        scan_location = jitter_location(position)

    try:
        cell_ids = util.get_cell_ids(scan_location[0], scan_location[1])
        timestamps = [0, ] * len(cell_ids)
        req = api.create_request()
        response = req.get_map_objects(latitude=f2i(scan_location[0]),
                                       longitude=f2i(scan_location[1]),
                                       since_timestamp_ms=timestamps,
                                       cell_id=cell_ids)
        #response = req.check_challenge()
        #response = req.get_hatched_eggs()
        #response = req.get_inventory()
        #response = req.check_awarded_badges()
        #response = req.download_settings()
        response = req.get_buddy_walked()
        response = req.call()
        return response

    except Exception as e:
        print('Exception while downloading map: %s', repr(e))
    return False

def encounter(api, eid, sid, lat, lng):
    try:
        req = api.create_request()
        encounter_result = req.encounter(
            encounter_id=b64encode(str(eid)),
            spawn_point_id=str(sid),
            player_latitude=float(lat),
            player_longitude=float(lng))
        #encounter_result = req.check_challenge()
        #encounter_result = req.get_hatched_eggs()
        #encounter_result = req.get_inventory()
        #encounter_result = req.check_awarded_badges()
        #encounter_result = req.download_settings()
        #encounter_result = req.get_buddy_walked()
        encounter_result = req.call()

        if (encounter_result is not None and 'wild_pokemon' in encounter_result['responses']['ENCOUNTER']):
            pokemon_info = encounter_result['responses']['ENCOUNTER']['wild_pokemon']['pokemon_data']

            pokemon = {
                'encounter_id': b64encode(str(eid)),
                'spawnpoint_id': sid,
                'pokemon_id': pid,
                'latitude': lat,
                'longitude': lng,
                'disappear_time': disappear_time,
                'individual_attack': pokemon_info.get('individual_attack', 0),
                'individual_defense': pokemon_info.get('individual_defense', 0),
                'individual_stamina': pokemon_info.get('individual_stamina', 0),
                'move_1': pokemon_info['move_1'],
                'move_2': pokemon_info['move_2'],
                'height': pokemon_info['height_m'],
                'weight': pokemon_info['weight_kg'],
                'gender': pokemon_info['pokemon_display']['gender'],
                'cp': pokemon_info['cp']
            }
        else:
            pokemon = False

        return pokemon

    except Exception as e:
        return e
    return False

@route('/vsnipe/', method = 'POST')
def vsnipe():
    eid = request.forms.get('eid')
    sid = request.forms.get('sid')
    lat = request.forms.get('lat')
    lng = request.forms.get('lng')

    api = initApi(lat, lng)
    user = login(api)
    
    position = [float(lat), float(lng), float(6.66)]
    map_dict = map_request(api, position)
    cells = map_dict['responses']['GET_MAP_OBJECTS']['map_cells']
    for cell in cells:
         wild_pokemon += cell.get('wild_pokemons', [])
    
    print(wild_pokemon)
    time.sleep(5)
    response = encounter(api, eid, sid, lat, lng)

    try:
        if response is not False:
            pokemon = response
        else:
            pokemon = response
        rv = [{'pokemon': str(pokemon)}]
    except KeyError, e:
        rv = [{'error': str(e)}]

    return dict(data=rv)

run(host=host, port=port, debug=True)
