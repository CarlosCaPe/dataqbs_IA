#!/usr/bin/env python3
import json
from pathlib import Path
import time
from pprint import pprint

from arbitraje.engine_techniques import scan_arbitrage

SNAP = Path(__file__).resolve().parents[1] / 'artifacts' / 'arbitraje' / 'offline_snapshot_profitable.json'
assert SNAP.exists(), f"Snapshot not found: {SNAP}"

payload = json.loads(SNAP.read_text(encoding='utf-8'))

cfg = {
    'techniques': {
        'enabled': ['bellman_ford'],
        'inline': ['bellman_ford'],
        'telemetry_file': None,
        'use_numba': False,
    },
    'bf': {},
}

snapid = payload.get('ts') or f"snap-{int(time.time())}"
print('Running scan_arbitrage on offline snapshot:', SNAP)
res = scan_arbitrage(snapid, payload, cfg)
print('FOUND', len(res), 'results')
if res:
    pprint(res[:10])
else:
    print('No results found')
