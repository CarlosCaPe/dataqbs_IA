"""Precompute simple volatility per token for offline snapshots and write an augmented snapshot.

Usage:
  python tools/precompute_snapshot.py --in artifacts/arbitraje/offline_snapshot_profitable.json --out artifacts/arbitraje/offline_snapshot_profitable_precomputed.json --window 5
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--in", dest="infile", required=True)
parser.add_argument("--out", dest="outfile", required=True)
parser.add_argument("--window", dest="window", type=int, default=5)
args = parser.parse_args()

p_in = Path(args.infile)
p_out = Path(args.outfile)
if not p_in.exists():
    print("input snapshot not found", p_in)
    raise SystemExit(2)

with open(p_in, "r", encoding="utf-8") as fh:
    data = json.load(fh)

out = {}
for key, payload in data.items():
    tickers = payload.get("tickers") or {}
    vol_map = {}
    for sym, t in tickers.items():
        if "/" not in sym:
            continue
        a, b = sym.split("/")
        hist = t.get("history") or t.get("ticks") or []
        mids = []
        try:
            for tick in hist[-args.window:]:
                bid = tick.get("bid")
                ask = tick.get("ask")
                if bid is not None and ask is not None:
                    mids.append((float(bid) + float(ask)) / 2.0)
                else:
                    mids.append(float(tick.get("price") or tick.get("px") or 0.0))
        except Exception:
            mids = []
        if len(mids) >= 2:
            mean = sum(mids) / len(mids)
            var = sum((x - mean) ** 2 for x in mids) / max(1, (len(mids) - 1))
            v = float(var ** 0.5)
        else:
            v = 0.0
        vol_map[a] = max(vol_map.get(a, 0.0), v)
        vol_map[b] = max(vol_map.get(b, 0.0), v)
    payload_copy = dict(payload)
    payload_copy["_precomputed_volatility"] = vol_map
    out[key] = payload_copy

p_out.parent.mkdir(parents=True, exist_ok=True)
with open(p_out, "w", encoding="utf-8") as fh:
    json.dump(out, fh)

print("wrote", p_out)
