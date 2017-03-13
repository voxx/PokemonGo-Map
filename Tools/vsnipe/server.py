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
    scan_location = jitter_location(position)

    try:
        cell_ids = util.get_cell_ids(scan_location[0], scan_location[1])
        timestamps = [0, ] * len(cell_ids)
        req = api.create_request()
        response = req.get_map_objects(latitude=f2i(scan_location[0]),
                                       longitude=f2i(scan_location[1]),
                                       since_timestamp_ms=timestamps,
                                       cell_id=cell_ids)
        response = req.check_challenge()
        #response = req.get_hatched_eggs()
        #response = req.get_inventory()
        #response = req.check_awarded_badges()
        #response = req.download_settings()
        #response = req.get_buddy_walked()
        response = req.call()
        return response

    except Exception as e:
        print('Exception while downloading map: %s', repr(e))
    return False

def encounter(api, eid, sid, lat, lng, pid, tth):
    try:
        req = api.create_request()
        encounter_result = req.encounter(
            encounter_id=eid,
            spawn_point_id=sid,
            player_latitude=lat,
            player_longitude=lng)
        encounter_result = req.call()

        if (encounter_result is not None and 'wild_pokemon' in encounter_result['responses']['ENCOUNTER']):
            pokemon_info = encounter_result['responses']['ENCOUNTER']['wild_pokemon']['pokemon_data']

            pokemon = {
                'encounter_id': b64encode(str(eid)),
                'spawnpoint_id': sid,
                'pokemon_id': pid,
                'latitude': lat,
                'longitude': lng,
                'disappear_time': tth,
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
    #eid = request.forms.get('eid')
    #sid = request.forms.get('sid')
    lat = request.forms.get('lat')
    lng = request.forms.get('lng')
    pid = request.forms.get('pid')

    api = initApi(lat, lng)
    user = login(api)
    time.sleep(10)
    position = [float(lat), float(lng), float(6.66)]
    map_dict = map_request(api, position)
    cells = map_dict['responses']['GET_MAP_OBJECTS']['map_cells']
    wild_pokemon = []
    
    for cell in cells:
        wild_pokemon += cell.get('wild_pokemons', [])
    
    response = False
    print(wild_pokemon)
    
    for pokemon in wild_pokemon:
        if pokemon['pokemon_data']['pokemon_id'] == int(pid):
            time.sleep(10)
            #response = encounter(api, pokemon['encounter_id'], sid, lat, lng, pid, pokemon['time_till_hidden_ms'])
            response = encounter(api, pokemon['encounter_id'], pokemon['spawn_point_id'], lat, lng, pid, pokemon['time_till_hidden_ms'])
            print(response)

    try:
        if response is not False:
            pokemon = response
        else:
            pokemon = False
        rv = [{'pokemon': str(pokemon)}]
    except KeyError, e:
        rv = [{'error': str(e)}]

    return dict(data=rv)

run(host=host, port=port, debug=True)
