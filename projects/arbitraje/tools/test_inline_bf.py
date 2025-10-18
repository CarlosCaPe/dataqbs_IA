from pathlib import Path
import json
import time

# Import the worker function directly
from arbitraje.engine_techniques import _tech_bellman_ford

# Build a tiny synthetic payload with two tickers forming a cycle
payload = {
    "snapshot_id": "test-inline",
    "ex_id": "local-test",
    "ts": int(time.time()),
    "tokens": ["A", "B", "USDT"],
    "fee": 0.1,
    "tickers": {
        "A/USDT": {"bid": 2.0, "ask": 2.05, "last": 2.02, "quoteVolume": 1000},
        "USDT/A": {"bid": 0.49, "ask": 0.51, "last": 0.5, "quoteVolume": 800},
    },
}

# Create a minimal config dict that matches expected structure
cfg = {
    "techniques": {"telemetry_file": "./artifacts/arbitraje/techniques_telemetry_test_inline.log"},
    "bf": {"min_net": -100.0, "min_net_per_hop": -100.0},
}

print('Running inline _tech_bellman_ford test...')
res = _tech_bellman_ford('test-inline', payload, cfg)
print('Result count:', len(res))

# Print diagnostic files for inspection
base = Path(__file__).resolve().parents[1]
paths = [
    base / 'src' / 'artifacts' / 'arbitraje' / 'diagnostics.log',
    base / 'artifacts' / 'arbitraje' / 'diagnostics.log',
    base.parent / 'artifacts' / 'arbitraje' / 'diagnostics.log',
    base / 'artifacts' / 'arbitraje' / 'techniques_telemetry_test_inline.log',
]

for p in paths:
    try:
        print('---', p)
        if p.exists():
            txt = p.read_text(encoding='utf-8')
            print(txt[-2000:])
        else:
            print('MISSING')
    except Exception as e:
        print('ERR', e)
