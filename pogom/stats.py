#!/usr/bin/python
# -*- coding: utf-8 -*-

# Get player stats from response_dict
def get_player_stats(response_dict):
    inventory_items = response_dict.get('responses', {})\
        .get('GET_INVENTORY', {}).get('inventory_delta', {})\
        .get('inventory_items', [])
    for item in inventory_items:
        item_data = item.get('inventory_item_data', {})
        if 'player_stats' in item_data:
            return item_data['player_stats']
    return {}


# Print statistics about accounts
def print_account_stats(rows, thread_status, account_queue, account_captchas,
                        account_failures, current_page):
    rows.append('-----------------------------------------')
    rows.append('Account statistics:')
    rows.append('-----------------------------------------')

    # Collect all accounts.
    accounts = []
    for item in thread_status:
        if thread_status[item]['type'] == 'Worker':
            worker = thread_status[item]
            account = worker.get('account', {})
            accounts.append(('active', account))
    for account in list(account_queue.queue):
        accounts.append(('spare', account))
    for captcha_tuple in list(account_captchas):
        account = captcha_tuple[1]
        accounts.append(('captcha', account))
    for acc_fail in account_failures:
        account = acc_fail['account']
        accounts.append(('failed', account))

    # Determine maximum username length.
    userlen = 4
    for status, acc in accounts:
        userlen = max(userlen, len(acc.get('username', '')))

    # Print table header.
    row_tmpl = '{:7} | {:' + str(userlen) + '} | {:5} | {:>8} | {:10} | {:6}' \
               ' | {:8} | {:5} | {:>10}'
    rows.append(row_tmpl.format('Status', 'User', 'Level', 'XP', 'Encounters',
                                'Throws', 'Captures', 'Spins', 'Walked'))

    # Pagination.
    start_line, end_line, total_pages = calc_pagination(len(accounts), 6, current_page)

    # Print account statistics.
    current_line = 0
    for status, account in accounts:
        # Skip over items that don't belong on this page.
        current_line += 1
        if current_line < start_line:
            continue
        if current_line > end_line:
            break

        # Format walked km
        km_walked_f = account.get('km_walked', 'none')
        if km_walked_f != 'none':
            km_walked_str = '{:.1f} km'.format(km_walked_f)
        else:
            km_walked_str = ""

        rows.append(row_tmpl.format(
            status,
            account.get('username', ''),
            account.get('level', ''),
            account.get('experience', ''),
            account.get('pokemons_encountered', ''),
            account.get('pokeballs_thrown', ''),
            account.get('pokemons_captured', ''),
            account.get('poke_stop_visits', ''),
            km_walked_str))

return total_pages
