#!/usr/bin/python
# -*- coding: utf-8 -*-

import argparse
import json
import os
import random
import sys
import time

from bottle import run, post, request, response, route
from os.path import dirname, abspath, join

from pgoapi import PGoApi
from pgoapi.exceptions import AuthException, NotLoggedInException, BannedAccountException
from pgoapi.utilities import f2i
from pgoapi import utilities as util

rm = abspath(dirname(dirname(dirname(abspath(__file__))))) # Path to RocketMap
sys.path.append(rm)
from pogom.utils import generate_device_info

vsc = join(abspath(join(__file__, os.pardir)), 'config/config.json') # Path to VSnipe Config
with open(vsc) as json_data_file:
    config = json.load(json_data_file)

host = config['server']['host']
port = int(config['server']['port'])

#accounts = config['accounts']
#random.shuffle(accounts)
parser = argparse.ArgumentParser(description='Process command line input.')
parser.add_argument('-csv', help=('Load accounts from CSV file containing ' +
                    '"auth_service,username,passwd" lines.'), default=False)
parser.parse_args()

csv = args.csv
if csv:
    account = get_random_account(csv)
else:
    account = get_random_account(rm + 'workers/vsnipe.csv')

hkeys = config['hash_key']
random.shuffle(hkeys)

def initApi(lat, lng):
    location = [float(lat), float(lng)]

    device_info = generate_device_info()
    api = PGoApi(device_info=device_info)

    hkey = random.choice(hkeys)
    if 'True' in hkey['enabled']:
        print('Using key {} for this request.'.format(hkey['key']))
        api.activate_hash_server(hkey['key'])

    api.set_position(*location)

    return api

def login(api):
    #account = random.choice(accounts)
    provider = account['provider']
    username = account['username']
    password = account['password']
    print('Using account {} for this request.'.format(account['username']))

    # Try to login. Repeat up to two times, but don't get stuck here.
    num_tries = 0
    while num_tries < 2:
        try:
            api.set_authentication(
                provider=provider,
                username=username,
                password=password)
            print('Login successful for account {}.'.format(account['username']))
            rv = [{'auth_status':'success'}]
            break
        except AuthException as e:
            num_tries += 1
            print('Login failed for account {}. Trying again in 30 seconds. Error: {}'.format(account['username'], repr(e)))
            rv = [{'auth_status':'fail', 'error':str(e)}]
            time.sleep(30)
        except BannedAccountException as e:
            print('Login failed for account {}. It appears to be banned. Error: {}'.format(account['username'], repr(e)))
            rv = [{'auth_status':'banned', 'error':str(e)}]
            break

    if num_tries >= 2:
        print(('Failed to login to account {} after {} attempts. Giving up.').format(account['username'], num_tries))

    return dict(data=rv)

def map_request(api, position):
    scan_location = position
    print('Using location {} for this request.'.format(str(position)))

    try:
        cell_ids = util.get_cell_ids(scan_location[0], scan_location[1])
        timestamps = [0, ] * len(cell_ids)
        req = api.create_request()
        req.get_map_objects(latitude=f2i(scan_location[0]),
                                       longitude=f2i(scan_location[1]),
                                       since_timestamp_ms=timestamps,
                                       cell_id=cell_ids)
        req.check_challenge()
        response = req.call()
        return response

    except Exception as e:
        print('Exception while downloading map: %s', repr(e))
    return False

def encounter(api, eid, sid, lat, lng, pid, tth):
    try:
        req = api.create_request()
        req.encounter(
            encounter_id=eid,
            spawn_point_id=sid,
            player_latitude=lat,
            player_longitude=lng)
        encounter_result = req.call()

        if (encounter_result is not None and 'wild_pokemon' in encounter_result['responses']['ENCOUNTER']):
            pokemon_info = encounter_result['responses']['ENCOUNTER']['wild_pokemon']['pokemon_data']

            level = 0
            cpm = pokemon_info['cp_multiplier']
            if cpm < 0.734:
                level = 58.35178527 * cpm * cpm - 2.838007664 * cpm + 0.8539209906
            else:
                level = 171.0112688 * cpm - 95.20425243
            level = int((round(level) * 2) / 2.0)

            pokemon = {
                'encounter_id': str(eid),
                'spawnpoint_id': str(sid),
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
                'cp': pokemon_info['cp'],
                'level': level
            }
        else:
            pokemon = False

        return pokemon

    except Exception as e:
        return e
    return False

def get_random_account(afile):
    # Load single random line from csv file instead of loading entire file.
    line = next(afile)
    for num, aline in enumerate(afile):
        if random.randrange(num + 2): continue
        line = aline

    # Count fields contained in line.
    num_fields = line.count(',') + 1

    # If the number of fields is not 3 this is not a valid CSV entry.
    if num_fields != 3:
        print('Error parsing CSV file on line: {}'.format(str(num)))
        sys.exit(1)
    else:
        line = line.strip()

    account = []
    fields = []
    field_error = ''

    # Get individual values from line and cleanup.
    fields = line.split(",")
    fields = map(str.strip, fields)

    # If field 0 is not ptc or google something is wrong!
    if (fields[0].lower() == 'ptc' or fields[0].lower() == 'google'):
        account['provider'] = fields[0]
    else:
        field_error = 'method'

    # If field length is not longer then 0 something is wrong!
    if len(fields[1]) > 0:
        account['username'] = fields[1]
    else:
        field_error = 'username'

    # If field length is not longer then 0 something is wrong!
    if len(fields[2]) > 0:
        account['password'] = fields[2]
    else:
        field_error = 'password'

    # If something is wrong display error.
    if field_error != '':
        print('Error parsing CSV on line {}. Error: {}'.format(str(num), field_error)
        sys.exit(1)

    return account

@route('/vsnipe/', method = 'POST')
def vsnipe():
    lat = request.forms.get('lat')
    lng = request.forms.get('lng')
    pid = request.forms.get('pid')
    position = [float(lat), float(lng), float(random.uniform(102.1, 249.7))]

    api = initApi(lat, lng)

    user = login(api)
    if "auth_status" in user['data'][0]:
        if user['data'][0]['auth_status'] == "success":
            time.sleep(5)
        else:
            return user

    map_dict = map_request(api, position)
    if map_dict is not None and map_dict['status_code'] == 3:
        rv = [{'error':'banned'}]
        print('Map request returned error: {}.'.format(str(rv)))
        return dict(data=rv)
    else:
        time.sleep(5)

    wild_pokemon = []
    cells = map_dict['responses']['GET_MAP_OBJECTS']['map_cells']
    for cell in cells:
        wild_pokemon += cell.get('wild_pokemons', [])
    print('Map request returned {}.'.format(str(wild_pokemon)))

    print('Checking for pokemon id {} in map response object.'.format(pid))
    response = False
    for pokemon in wild_pokemon:
        if (pokemon['pokemon_data']['pokemon_id']) == int(pid) and (str(pokemon['latitude']).find(str(lat)) != -1) and (str(pokemon['longitude']).find(str(lng)) != -1):
            print('Found pokemon id {} in map response object. Starting encounter.'.format(pid))
            response = encounter(api, pokemon['encounter_id'], pokemon['spawn_point_id'], lat, lng, pid, pokemon['time_till_hidden_ms'])
            print('Encounter request returned {}.'.format(str(response)))

    try:
        if response is not False:
            pokemon = response
        else:
            pokemon = False
            print('Pokemon id {} was not found.'.format(pid))
        rv = [{'pokemon': str(pokemon)}]
    except KeyError, e:
        rv = [{'error': str(e)}]

    return dict(data=rv)

run(host=host, port=port, debug=True)
