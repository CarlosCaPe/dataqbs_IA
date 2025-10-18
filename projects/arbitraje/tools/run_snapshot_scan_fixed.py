#!/usr/bin/env python3
"""Run scan_arbitrage against an offline snapshot by converting it to the
expected payload shape.

Usage: python run_snapshot_scan_fixed.py [exchange]
If exchange is omitted, picks the first exchange in the snapshot (prefer 'binance').
"""
import json
import sys
from pathlib import Path
from pprint import pprint

from arbitraje.engine_techniques import scan_arbitrage

SNAP = Path(__file__).resolve().parents[1] / 'artifacts' / 'arbitraje' / 'offline_snapshot_profitable.json'
if not SNAP.exists():
    raise SystemExit(f"Snapshot not found: {SNAP}")

raw = json.loads(SNAP.read_text(encoding='utf-8'))
ex_choice = None
if len(sys.argv) > 1:
    ex_choice = sys.argv[1]
# prefer binance if present
if not ex_choice:
    if 'binance' in raw:
        ex_choice = 'binance'
    else:
        ex_choice = next(iter(raw.keys()))

print('Using exchange:', ex_choice)
ex_data = raw.get(ex_choice) or {}
markets = ex_data.get('markets') or {}
tickers = ex_data.get('tickers') or {}

# derive tokens from markets
tokens = set()
for sym, m in markets.items():
    # some snapshots use base/quote in markets, otherwise parse symbol
    b = m.get('base')
    q = m.get('quote')
    if b:
        tokens.add(str(b))
    if q:
        tokens.add(str(q))
    if (not b or not q) and '/' in sym:
        a, c = sym.split('/')
        tokens.add(a)
        tokens.add(c)

# remove common stable base if present as a quote target for triangle tests
if 'USDT' in tokens and len(tokens) > 3:
    # keep it; leave tokens as-is — engine tests expect tokens list like ['A','B','C']
    pass

# minimal payload for engine
payload = {
    'ex_id': ex_choice,
    'ts': 'offline-snap',
    'tokens': list(tokens),
    'tickers': tickers,
    'fee': 0.10,
    'min_quote_vol': 0.0,
    'min_net': 0.0,
}

cfg = {'techniques': {'enabled': ['bellman_ford', 'stat_tri'], 'inline': ['bellman_ford', 'stat_tri'], 'telemetry_file': None}}

print('tokens:', payload['tokens'])
print('tickers count:', len(payload['tickers']))
print('Running scan...')
res = scan_arbitrage('offline-snap', payload, cfg)
print('FOUND', len(res), 'results')
if res:
    pprint(res[:10])
else:
    print('No results found')
