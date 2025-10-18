#!/usr/bin/env python3
import json
import time
from pathlib import Path
from pprint import pprint

from arbitraje.engine_techniques import scan_arbitrage

SNAP = Path(__file__).resolve().parents[1] / 'artifacts' / 'arbitraje' / 'offline_snapshot_profitable.json'
if not SNAP.exists():
    raise SystemExit(f"Snapshot not found: {SNAP}")
raw = json.loads(SNAP.read_text(encoding='utf-8'))
ex = 'binance' if 'binance' in raw else next(iter(raw.keys()))
ex_data = raw.get(ex)
markets = ex_data.get('markets') or {}
tickers = ex_data.get('tickers') or {}

# derive tokens
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
    'ts': f'dump-test-{int(time.time())}',
    'tokens': list(tokens),
    'tickers': tickers,
    'fee': 0.10,
    'min_quote_vol': 0.0,
    'min_net': 0.0,
}

cfg = {
    'techniques': {
        'enabled': ['bellman_ford'],
        'inline': ['bellman_ford'],
        'dump_graph': True,
    }
}

print('Running scan with dump_graph enabled...')
res = scan_arbitrage(payload['ts'], payload, cfg)
print('scan returned', len(res), 'results')

# find latest file
art_dir = Path(__file__).resolve().parents[1] / 'artifacts' / 'arbitraje'
files = sorted(art_dir.glob('graph_debug_*.jsonl'), key=lambda p: p.stat().st_mtime)
if not files:
    print('No graph debug files found')
else:
    print('Latest debug file:', files[-1])
    print('Tail content:')
    print(files[-1].read_text(encoding='utf-8').splitlines()[-1])
