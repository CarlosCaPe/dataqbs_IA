#!/usr/bin/env python3
import json
import sys
from pathlib import Path

from arbitraje.engine_techniques import _tech_bellman_ford

SNAP = Path(__file__).resolve().parents[1] / 'artifacts' / 'arbitraje' / 'offline_snapshot_profitable.json'
if not SNAP.exists():
    raise SystemExit(f"Snapshot not found: {SNAP}")
raw = json.loads(SNAP.read_text(encoding='utf-8'))
ex = 'binance'
if ex not in raw:
    ex = next(iter(raw.keys()))
payload = raw.get(ex)
# call function but monkeypatch print via diag_log path absence
res = _tech_bellman_ford('snap-test', payload, {'techniques': {'use_numba': False}})
print('RES LEN', len(res))
print('Done')
