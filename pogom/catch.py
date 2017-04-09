#!/usr/bin/python
# -*- coding: utf-8 -*-

import logging
import time

log = logging.getLogger(__name__)

def catch(api, eid, sid, pid):
    # Try to catch pokemon, but don't get stuck.
    attempts = 0
    while attempts < 4:
        log.info('Starting attempt %s to catch %s!', attempt, pid)
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
            catch_result = req.call()

            if (catch_result is not None and 'CATCH_POKEMON' in catch_result['responses']):
                catch_status = catch_result['responses']['CATCH_POKEMON']['status'];
                # Success!
                if catch_status == 1:
                    cpid = catch_result['responses']['CATCH_POKEMON']['captured_pokemon_id']
                    log.info('Catch attempt %s was successful for pid: %s! The cpid is %s.', attempt, pid, cpid)
                    rv = [{'catch_status':'success', 'cpid':cpid}]
                    break

                # Broke free!
                if catch_status == 2:
                    log.info('Catch attempt %s failed for pid: %s. It broke free!', attempt, pid)

                # Ran away!
                if catch_status == 3:
                    log.info('Catch attempt %s failed for pid: %s. It ran away!', attempt, pid)
                    rv = [{'catch_status':'ran'}]
                    break

                # Dodged!
                if catch_status == 4:
                    log.info('Catch attempt %s failed for pid: %s. It dodged the ball!', attempt, pid)

            else:
                log.error('Catch attempt %s failed for pid: %s. The api response was empty!', attempt, pid)

        except Exception as e:
            log.error('Catch attempt %s failed for pid: %s. The api response returned an error!', attempt, pid)
            rv = [{'catch_status':'error', 'error':str(e)}]

        attempts += 1
        time.sleep(10)

    if attempts >= 4:
        log.error('Failed to catch pid: %s after %s attempts. Giving up.', pid, attempts)
        rv = [{'catch_status':'fail'}]

     dict(data=rv)
