"""Analyze outputs and telemetry to compute detections >= 0.01% and latency quantiles."""

from __future__ import annotations
import csv
import json
from pathlib import Path
from statistics import median


def percentile(sorted_vals, p):
    if not sorted_vals:
        return 0.0
    n = len(sorted_vals)
    pos = p * (n - 1)
    lo = int(pos)
    hi = min(n - 1, lo + 1)
    if lo == hi:
        return sorted_vals[int(pos)]
    return sorted_vals[lo] + (pos - lo) * (sorted_vals[hi] - sorted_vals[lo])


OUTDIR = Path("../../artifacts/arbitraje/outputs").resolve()
ARTDIR = Path("../../projects/arbitraje/artifacts/arbitraje").resolve()
TECH_LOG = Path(
    "../../projects/arbitraje/artifacts/arbitraje/techniques_telemetry.log"
).resolve()
RADAR_LOG = Path(
    "../../projects/arbitraje/artifacts/arbitraje/radar_dryrun_1000.log"
).resolve()

files = {
    "bf_csv": OUTDIR / "arbitrage_bf_usdt_ccxt.csv",
    "sim_csv": OUTDIR / "arbitrage_bf_simulation_usdt_ccxt.csv",
}

# parse BF csv
bf_rows = []
if files["bf_csv"].exists():
    with open(files["bf_csv"], "r", encoding="utf-8") as fh:
        rdr = csv.DictReader(fh)
        for r in rdr:
            bf_rows.append(r)

sim_rows = []
if files["sim_csv"].exists():
    with open(files["sim_csv"], "r", encoding="utf-8") as fh:
        rdr = csv.DictReader(fh)
        for r in rdr:
            sim_rows.append(r)


# count detections with net_bps_est >= 1.0 (1 bps)
def count_ge(rows, key="net_bps_est", threshold=1.0):
    c = 0
    picked = []
    for r in rows:
        try:
            nb = float(r.get(key) or 0.0)
            if nb >= threshold:
                c += 1
                picked.append(r)
        except Exception:
            continue
    return c, picked


bf_count, bf_picked = count_ge(bf_rows, "net_bps_est", 1.0)
sim_count, sim_picked = count_ge(sim_rows, "net_bps_est", 1.0)

# parse techniques telemetry durations (duration_s)
durations = []
telemetry_files = [
    TECH_LOG,
    Path("../../artifacts/arbitraje/techniques_telemetry.log").resolve(),
    Path("../../artifacts/arbitraje/telemetry_before.log").resolve(),
    Path("../../artifacts/arbitraje/telemetry_after.log").resolve(),
]
for tf in telemetry_files:
    if tf.exists():
        try:
            with open(tf, "r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                        if "duration_s" in obj:
                            durations.append(
                                float(obj.get("duration_s") or 0.0) * 1000.0
                            )
                    except Exception:
                        continue
        except Exception:
            continue

sorted_d = sorted(durations)
res = {
    "bf_csv_rows": len(bf_rows),
    "bf_ge_1bps": bf_count,
    "sim_csv_rows": len(sim_rows),
    "sim_ge_1bps": sim_count,
    "telemetry_samples": len(sorted_d),
    "p50_ms": percentile(sorted_d, 0.5),
    "p90_ms": percentile(sorted_d, 0.9),
    "p99_ms": percentile(sorted_d, 0.99),
}

print(json.dumps(res, indent=2))

# write sample picks to artifacts for inspection
out_dir = Path("../../artifacts/arbitraje/analysis")
out_dir.mkdir(parents=True, exist_ok=True)
with open(out_dir / "bf_picked_sample.json", "w", encoding="utf-8") as fh:
    json.dump(bf_picked[:50], fh, indent=2)
with open(out_dir / "sim_picked_sample.json", "w", encoding="utf-8") as fh:
    json.dump(sim_picked[:50], fh, indent=2)
print("wrote samples to", out_dir)
