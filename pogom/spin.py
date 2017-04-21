#!/usr/bin/python
# -*- coding: utf-8 -*-

import logging
import time
import random

from .utils import in_radius

log = logging.getLogger(__name__)


# Perform a Pokestop spin and drops most items.
# Adapted from sLoPPydrive
def spin_and_drop(api, map_dict, fort, step_location, account):
    if fort.get('type') == 1:
        if pokestop_spinnable(fort, step_location):
            if spin_pokestop(api, fort, step_location, account):
                log.info('Account %s successfully spun a pokestop.', account['username'])

            log.info("Checking if items need to be dropped for account %s.", account['username'])
            drop_items(api, map_dict, 1, 200, 0.10, "Poke Ball")
            drop_items(api, map_dict, 2, 1, 1.0, "Great Ball")
            drop_items(api, map_dict, 3, 10, 0.80, "Ultra Ball")
            drop_items(api, map_dict, 101, 10, 1.0, "Potion")
            drop_items(api, map_dict, 102, 10, 1.0, "Super Potion")
            drop_items(api, map_dict, 103, 10, 1.0, "Hyper Potion")
            drop_items(api, map_dict, 104, 10, 1.0, "Max Potion")
            drop_items(api, map_dict, 201, 10, 1.0, "Revive")
            drop_items(api, map_dict, 202, 10, 1.0, "Max Revive")
            drop_items(api, map_dict, 701, 10, 1.0, "Razz Berry")
            drop_items(api, map_dict, 703, 10, 1.0, "Nanab Berry")
            drop_items(api, map_dict, 705, 10, 1.0, "Pinap Berry")
            return True

    return False


def spin_pokestop(api, fort, step_location, account):
    log.info('Attempting to spin pokestop for account %s.', account['username'])

    time.sleep(random.uniform(0.8, 1.8))  # Do not let Niantic throttle
    spin_response = spin_pokestop_request(api, fort, step_location)
    time.sleep(random.uniform(2, 4))  # Do not let Niantic throttle

    # Check for reCaptcha
    captcha_url = spin_response['responses']['CHECK_CHALLENGE']['challenge_url']
    if len(captcha_url) > 1:
        log.info('Account encountered a captcha!')
        return False

    spin_result = spin_response['responses']['FORT_SEARCH']['result']
    if spin_result is 1:
        return True
    elif spin_result is 2:
        log.info('Unable to spin pokestop. Out of range!')
    elif spin_result is 3:
        log.info('Failed to spin pokestop. Needs to cool down!')
    elif spin_result is 4:
        log.info('Failed to spin pokestop. Inventory is full!')
    elif spin_result is 5:
        log.info('Maximum number of pokestops spun for today!')
    else:
        log.info('Failed to spin a pokestop. Unknown result %d.', spin_result)

    return False


def pokestop_spinnable(fort, step_location):
    spinning_radius = 0.04
    in_range = in_radius((fort['latitude'], fort['longitude']), step_location, spinning_radius)
    now = time.time()
    needs_cooldown = "cooldown_complete_timestamp_ms" in fort and fort["cooldown_complete_timestamp_ms"] / 1000 > now
    if not in_range:
        log.debug('Pokestop was out of range!')

    return in_range and not needs_cooldown


def spin_pokestop_request(api, fort, step_location):
    try:
        req = api.create_request()
        req.fort_search(
            fort_id=fort['id'],
            fort_latitude=fort['latitude'],
            fort_longitude=fort['longitude'],
            player_latitude=step_location[0],
            player_longitude=step_location[1])
        req.check_challenge()
        req.get_inventory()
        spin_pokestop_response = req.call()

        return spin_pokestop_response

    except Exception as e:
        log.warning('Exception while spinning pokestop: %s', repr(e))

    return False


def get_item_count(map_dict, item_id):
    inventory_items = map_dict['responses'].get(
        'GET_INVENTORY', {}).get(
        'inventory_delta', {}).get(
        'inventory_items', [])
    item_data = [item['inventory_item_data']['item']
                 for item in inventory_items
                 if 'item' in item.get('inventory_item_data', {}) and
                    item['inventory_item_data']['item']['item_id'] == item_id]
    if len(item_data) > 0:
        return item_data[0].get('count', 0)

    return 0


def drop_items(api, map_dict, item_id, min_count, drop_fraction, item_name):
    item_count = get_item_count(map_dict, item_id)
    drop_count = int(item_count * drop_fraction)
    if item_count > min_count and drop_count > 0:
        result = drop_items_request(api, item_id, drop_count)
        if result == 1:
            log.info("Dropped {} {}s.".format(drop_count, item_name))
        else:
            log.warning("Failed dropping {} {}s.".format(drop_count, item_name))
    else:
        log.debug("Bag contains {} {}s. No need to drop any.".format(item_count, item_name))


def drop_items_request(api, item_id, amount):
    time.sleep(random.uniform(3, 5))
    try:
        req = api.create_request()
        req.recycle_inventory_item(item_id=item_id, count=amount)
        req.check_challenge()
        req.get_inventory()
        response_dict = req.call()
        if ('responses' in response_dict) and ('RECYCLE_INVENTORY_ITEM' in response_dict['responses']):
            drop_details = response_dict['responses']['RECYCLE_INVENTORY_ITEM']
            return drop_details.get('result', -1)

    except Exception as e:
        log.warning('Exception while dropping items: %s', repr(e))

    return False


# Send LevelUpRewards request to check for and accept level up rewards.
# @Returns
# 0: UNSET
# 1: SUCCESS
# 2: AWARDED_ALREADY
def level_up_rewards_request(api, player_level, account):
    log.info('Attempting to check level up rewards for account %s.', account['username'])
    time.sleep(random.uniform(2, 3))
    try:
        req = api.create_request()
        req.level_up_rewards(level=player_level)
        req.check_challenge()
        rewards_response = req.call()
        if ('responses' in rewards_response) and ('LEVEL_UP_REWARDS' in rewards_response['responses']):
            reward_details = rewards_response['responses']['LEVEL_UP_REWARDS']
            return reward_details.get('result', -1)

    except Exception as e:
        log.warning('Exception while requesting level up rewards: %s', repr(e))

    return False
