#!/usr/bin/env python3
"""Update FUND dashboard data.json from GeckoTerminal API."""
import requests, json, datetime, sys

TOKEN = '0xa02d9a9a5f5453463aa4855f62e47d9cc27086d9'
DATA_FILE = '/Users/roger/fundiora-tools/dashboard/data.json'
HISTORY_FILE = '/Users/roger/fundiora-tools/dashboard/history.json'
API_BASE = 'https://api.geckoterminal.com/api/v2'

def fetch():
    # Token data
    r = requests.get(f'{API_BASE}/networks/base/tokens/{TOKEN}', timeout=20, headers={'User-Agent':'Mozilla/5.0'})
    r.raise_for_status()
    data = r.json()['data']
    attrs = data['attributes']

    # Pool data from token relationship
    pools = data['relationships']['top_pools']['data']
    pool_detail = None
    if pools:
        raw_pool = pools[0]['id'].replace('base_','')
        r2 = requests.get(f'{API_BASE}/networks/base/pools/{raw_pool}', timeout=20, headers={'User-Agent':'Mozilla/5.0'})
        if r2.status_code == 200:
            p = r2.json()['data']['attributes']
            pool_detail = {
                'address': raw_pool,
                'name': p.get('name'),
                'reserve_usd': float(p['reserve_in_usd']) if p.get('reserve_in_usd') else 0,
                'base_price': float(p['base_token_price_usd']) if p.get('base_token_price_usd') else 0,
                'quote_price': float(p['quote_token_price_usd']) if p.get('quote_token_price_usd') else 0,
                'volume_24h': float(p['volume_usd'].get('h24',0)) if p.get('volume_usd') else 0,
                'volume_6h': float(p['volume_usd'].get('h6',0)) if p.get('volume_usd') else 0,
                'txns_24h': p.get('transactions',{}).get('h24',{'buys':0,'sells':0}),
                'txns_6h': p.get('transactions',{}).get('h6',{'buys':0,'sells':0}),
                'price_change_24h': float(p['price_change_percentage'].get('h24',0)) if p.get('price_change_percentage') else 0,
            }

    v24 = attrs['volume_usd'].get('h24')
    v24f = float(v24) if v24 else 0

    output = {
        'updated_at': datetime.datetime.now().isoformat(),
        'token': {
            'name': attrs['name'],
            'symbol': attrs['symbol'],
            'address': TOKEN,
            'decimals': attrs['decimals'],
            'price_usd': float(attrs['price_usd']),
            'fdv': float(attrs['fdv_usd']) if attrs.get('fdv_usd') else None,
            'market_cap': float(attrs['market_cap_usd']) if attrs.get('market_cap_usd') else None,
            'total_reserve_usd': float(attrs['total_reserve_in_usd']),
            'total_supply': float(attrs['normalized_total_supply']),
            'volume_24h': v24f,
            'pool_count': len(pools),
        },
        'pool': pool_detail,
        'source': 'geckoterminal'
    }

    with open(DATA_FILE, 'w') as f:
        json.dump(output, f, indent=2)

    # Append to history
    try:
        with open(HISTORY_FILE,'r') as f:
            hist = json.load(f)
    except:
        hist = []
    hist.append({'t': datetime.datetime.now().isoformat(), 'p': float(attrs['price_usd'])})
    # trim to 90 days
    cutoff = (datetime.datetime.now() - datetime.timedelta(days=90)).isoformat()
    hist = [h for h in hist if h['t'] > cutoff]
    with open(HISTORY_FILE,'w') as f:
        json.dump(hist, f, indent=2)

    print(f"Updated {DATA_FILE} at {output['updated_at']}")
    print(f"Price: ${output['token']['price_usd']:.8f} | FDV: ${output['token']['fdv']:,.2f} | Vol24h: ${output['token']['volume_24h']:,.2f}")

if __name__ == '__main__':
    fetch()
