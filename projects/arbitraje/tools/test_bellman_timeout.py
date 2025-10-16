import time

from arbitraje import engine_techniques

# Save original registry entry
orig = engine_techniques._TECHS.get("bellman_ford")


# Long-running fake technique to simulate a hang in process worker
def long_sleep(snapshot_id, edges, cfg):
    time.sleep(10)
    return [
        {
            "ts": snapshot_id,
            "venue": "test",
            "cycle": "A->B->C->A",
            "net_bps_est": 100.0,
        }
    ]


# Replace registry entry for process-executed technique only
engine_techniques._TECHS["bellman_ford"] = long_sleep

# Build a small payload: minimal tickers to allow original fallback to run if called
payload = {
    "ex_id": "test_ex",
    "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
    "tokens": ["USDT", "A", "B", "C"],
    "tickers": {
        "USDT/A": {"bid": 0.5, "ask": 0.5, "last": 0.5},
        "A/B": {"bid": 2.0, "ask": 2.0, "last": 2.0},
        "B/C": {"bid": 2.0, "ask": 2.0, "last": 2.0},
        "C/USDT": {"bid": 0.3, "ask": 0.3, "last": 0.3},
    },
    "fee": 0.1,
    "min_net": 0.0,
    "top": 5,
}

cfg = {
    "techniques": {
        "enabled": ["bellman_ford"],
        "max_workers": 1,
        "fallback_timeout": 1.0,
        "telemetry_file": "./artifacts/arbitraje/techniques_telemetry.log",
    }
}

print(
    "Running scan_arbitrage with simulated hang (process will sleep) and fallback_timeout=1.0s"
)
res = engine_techniques.scan_arbitrage("test_snap", payload, cfg)
print("scan_arbitrage returned:")
print(res)

# Show telemetry file tail if exists
try:
    with open(cfg["techniques"]["telemetry_file"], "r", encoding="utf-8") as fh:
        lines = fh.readlines()
        print("\nTelemetry file lines:")
        for ln in lines[-10:]:
            print(ln.strip())
except Exception as e:
    print("No telemetry file or couldn't read it:", e)

# Restore registry
engine_techniques._TECHS["bellman_ford"] = orig
