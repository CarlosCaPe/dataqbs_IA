#!/usr/bin/env python3
import logging
import sys
import time
from pathlib import Path

# Ensure project path
ROOT = Path(__file__).resolve().parents[1]
ART_DIR = ROOT / "artifacts" / "arbitraje"
ART_DIR.mkdir(parents=True, exist_ok=True)

# Configure logging to stdout
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
sh = logging.StreamHandler(sys.stdout)
sh.setLevel(logging.DEBUG)
logger.addHandler(sh)

# Import the engine function
from arbitraje.engine_techniques import scan_arbitrage

# Telemetry file path
telemetry_file = ART_DIR / "techniques_telemetry_relax.log"
# Remove existing telemetry file so we can observe new writes
try:
    telemetry_file.unlink()
except Exception:
    pass

snapshot_id = "debug_snap_{}".format(int(time.time()))
# Construct a minimal 3-token cycle payload that should produce a result
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
    "techniques": {
        "telemetry_file": str(telemetry_file),
        "enabled": ["bellman_ford"],
        # run inline to avoid pool/pickling and make writes deterministic
        "inline": ["bellman_ford"],
        "max_workers": 1,
        "fallback_timeout": 1.0,
    }
}

print("Running scan_arbitrage snapshot=", snapshot_id)
res = scan_arbitrage(snapshot_id, payload, cfg)
print("RESULTS:", res)
print("Telemetry file exists:", telemetry_file.exists())
if telemetry_file.exists():
    print("--- TELEMETRY CONTENT ---")
    print(telemetry_file.read_text())
else:
    print("Telemetry file missing or empty")
