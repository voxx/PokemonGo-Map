#!/usr/bin/python
# -*- coding: utf-8 -*-

import logging
import time

log = logging.getLogger(__name__)

def catch(api, eid, sid, pid):
    # Try to catch pokemon, but don't get stuck.
    attempts = 1
    while attempts < 3:
        log.info('Starting attempt %s to catch pid: %s!', attempts, pid)
        try:
            req = api.create_request()
            catch_result = req.catch_pokemon(
                encounter_id=eid,
                pokeball=1,
                normalized_reticle_size=1.950,
                spawn_point_id=sid,
                hit_pokemon=1,
                spin_modifier=1.0,
                normalized_hit_position=1.0)
            catch_result = req.check_challenge()
            catch_result = req.get_inventory()
            catch_result = req.call()

            if (catch_result is not None and 'CATCH_POKEMON' in catch_result['responses']):
                #log.info('DEBUG: %s', catch_result['responses']['CATCH_POKEMON'])
                catch_status = catch_result['responses']['CATCH_POKEMON']['status'];
                # Success!
                if catch_status == 1:
                    cpid = catch_result['responses']['CATCH_POKEMON']['captured_pokemon_id']
                    log.info('Catch attempt %s was successful for pid: %s! The cpid is %s.', attempts, pid, str(cpid))

                    # Check inventory for new pokemon id and movesets
                    iitems = catch_result['responses']['GET_INVENTORY']['inventory_delta']['inventory_items']
                    for item in iitems:
                        iidata = item['inventory_item_data']
                        if str(cpid) in str(item):
                            npid = item['inventory_item_data']['pokemon_data']['pokemon_id']
                            m1 = item['inventory_item_data']['pokemon_data']['move_1']
                            m2 = item['inventory_item_data']['pokemon_data']['move_2']

                    rv = [{'catch_status':'success', 'pid':npid, 'm1':m1, 'm2':m2}]

                    time.sleep(5)
                    released = release(api, pid, cpid)

                    break

                # Broke free!
                if catch_status == 2:
                    log.info('Catch attempt %s failed for pid: %s. It broke free!', attempts, pid)

                # Ran away!
                if catch_status == 3:
                    log.info('Catch attempt %s failed for pid: %s. It ran away!', attempts, pid)
                    rv = [{'catch_status':'ran'}]
                    break

                # Dodged!
                if catch_status == 4:
                    log.info('Catch attempt %s failed for pid: %s. It dodged the ball!', attempts, pid)

            else:
                log.error('Catch attempt %s failed for pid: %s. The api response was empty!', attempts, pid)

        except Exception as e:
            log.error('Catch attempt %s failed for pid: %s. The api response returned an error!', attempts, pid)
            rv = [{'catch_status':'error', 'error':str(e)}]

        attempts += 1
        time.sleep(5)

    if attempts >= 3:
        log.error('Failed to catch pid: %s after %s attempts. Giving up.', pid, attempts)
        rv = [{'catch_status':'fail'}]

    return dict(data=rv)

def release(api, pid, cpid):
    try:
        log.info('Attempting to release pid: %s', pid)
        req = api.create_request()
        release_result = req.release_pokemon(pokemon_id=cpid)
        release_result = req.check_challenge()
        release_result = req.get_inventory()
        release_result = req.call()

        if (release_result is not None and 'RELEASE_POKEMON' in release_result['responses']):
            #log.info('DEBUG: %s', release_result['responses']['RELEASE_POKEMON'])

            release_result = release_result['responses']['RELEASE_POKEMON']['result'];
            if int(release_result) == 1:
                log.info('Successfully released pid: %s', pid)
            else:
                log.info('Failed to release pid: %s with result code: %s.', pid, release_result)

    except Exception as e:
        log.error('Exception occured while releasing pid: %s Error: %s', pid, str(e))
        return False

    return True
