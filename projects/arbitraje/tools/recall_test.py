"""Run recall test on a precomputed snapshot comparing pruning ON vs OFF.

Outputs counts and sample cycles with net_pct >= target_min_net.
"""
from __future__ import annotations
import json
from pathlib import Path
from pprint import pprint

from arbitraje.engine_techniques import _tech_bellman_ford

SNAP = Path(__file__).resolve().parents[1] / "artifacts" / "arbitraje" / "offline_snapshot_profitable_precomputed.json"
if not SNAP.exists():
    print("snapshot missing", SNAP)
    raise SystemExit(2)

with open(SNAP, "r", encoding="utf-8") as fh:
    data = json.load(fh)

# pick first payload (or iterate all)
k = next(iter(data.keys()))
payload = data[k]

# baseline: pruning OFF
cfg_off = {"techniques": {"pruning_qvol_frac": 0.0, "pruning_degree_threshold": 0, "use_numba": False}}
res_off = _tech_bellman_ford(k, payload, cfg_off)

# pruning ON (conservative defaults)
cfg_on = {"techniques": {"pruning_qvol_frac": 0.05, "pruning_degree_threshold": 3, "use_numba": False}}
res_on = _tech_bellman_ford(k, payload, cfg_on)

# target threshold in percent (0.05% = 0.05)
TARGET = 0.05

def filter_target(res):
    out = []
    for r in res:
        try:
            nb = float(r.get("net_bps_est") or 0.0)
            # net_bps_est is in bps, 0.05% = 5 bps
            if nb >= 5.0:
                out.append(r)
        except Exception:
            continue
    return out

f_off = filter_target(res_off)
f_on = filter_target(res_on)

print("total_off:", len(res_off), "target_off:", len(f_off))
print("total_on:", len(res_on), "target_on:", len(f_on))

print("sample_off:")
for r in f_off[:10]:
    pprint(r)
print("sample_on:")
for r in f_on[:10]:
    pprint(r)

# show losses
lost = [r for r in f_off if r not in f_on]
print("lost_count:", len(lost))
for r in lost[:10]:
    pprint(r)
