#!/usr/bin/env python3
from pprint import pprint
from pathlib import Path
import time

from arbitraje.engine_techniques import _tech_bellman_ford

# Construct same payload as debug_scan
tickers = {
    "A/B": {"bid": "2.0", "ask": "2.0", "last": "2.0"},
    "B/C": {"bid": "3.0", "ask": "3.0", "last": "3.0"},
    "C/A": {"bid": "0.2", "ask": "0.2", "last": "0.2"},
}
payload = {
    "tickers": tickers,
    "tokens": ["A", "B", "C"],
    "fee": 0.1,
    "ts": int(time.time()),
    "ex_id": "debugex",
}

cfg = {
    "techniques": {"telemetry_file": None, "use_numba": False},
    "bf": {},
}

# We'll call the pure python path by disabling numba via cfg
print("Calling _tech_bellman_ford with payload:")
pprint(payload)

res = _tech_bellman_ford(payload.get("ts") or "snap", payload, cfg)
print('\nRESULTS:')
print(res)
