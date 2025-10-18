#!/usr/bin/env python3
import json
from pathlib import Path
from pprint import pprint

from arbitraje.engine_techniques import _tech_bellman_ford, scan_arbitrage

SNAP = Path(__file__).resolve().parents[1] / 'artifacts' / 'arbitraje' / 'offline_snapshot_profitable.json'
raw = json.loads(SNAP.read_text(encoding='utf-8'))
ex = 'binance'
if ex not in raw:
    ex = next(iter(raw.keys()))
ex_data = raw.get(ex)
# build payload like run_snapshot_scan_fixed
markets = ex_data.get('markets') or {}
tickers = ex_data.get('tickers') or {}

tokens = set()
for sym, m in markets.items():
    b = m.get('base')
    q = m.get('quote')
    if b:
        tokens.add(str(b))
    if q:
        tokens.add(str(q))

payload = {
    'ex_id': ex,
    'ts': 'offline-snap',
    'tokens': list(tokens),
    'tickers': tickers,
    'fee': 0.10,
    'min_quote_vol': 0.0,
    'min_net': 0.0,
}

cfg_inline = {'techniques': {'enabled': ['bellman_ford'], 'inline': ['bellman_ford'], 'telemetry_file': None, 'use_numba': False}}
print('Calling _tech_bellman_ford directly...')
d_direct = _tech_bellman_ford('snap', payload, {'techniques': {'use_numba': False}})
print('direct len', len(d_direct))
print('Calling scan_arbitrage with inline...')
d_scan = scan_arbitrage('snap', payload, cfg_inline)
print('scan len', len(d_scan))
if d_direct:
    print('direct sample:')
    pprint(d_direct[:5])
if d_scan:
    print('scan sample:')
    pprint(d_scan[:5])
