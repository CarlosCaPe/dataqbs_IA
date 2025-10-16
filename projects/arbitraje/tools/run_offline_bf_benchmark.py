"""Run Bellman-Ford on an offline snapshot N times and append per-scan telemetry.

Usage: python run_offline_bf_benchmark.py --iters 200
"""

import argparse
import json
import time
from pathlib import Path
import importlib.util
import sys

parser = argparse.ArgumentParser()
parser.add_argument("--iters", type=int, default=200)
parser.add_argument(
    "--snapshot",
    type=str,
    default=str(
        Path(__file__).resolve().parents[1]
        / "artifacts"
        / "arbitraje"
        / "offline_snapshot_profitable.json"
    ),
)
parser.add_argument(
    "--telemetry",
    type=str,
    default=str(
        Path(__file__).resolve().parents[1]
        / "artifacts"
        / "arbitraje"
        / "techniques_telemetry.log"
    ),
)
args = parser.parse_args()

# load engine_techniques by file path
ROOT_SRC = Path(__file__).resolve().parents[1] / "src"
mod_path = ROOT_SRC / "arbitraje" / "engine_techniques.py"
if not mod_path.exists():
    print("engine_techniques not found at", mod_path)
    raise SystemExit(2)
spec = importlib.util.spec_from_file_location("engine_techniques", str(mod_path))
engine_mod = importlib.util.module_from_spec(spec)
sys.modules["engine_techniques"] = engine_mod
spec.loader.exec_module(engine_mod)
bf = getattr(engine_mod, "_tech_bellman_ford")

snap_path = Path(args.snapshot)
if not snap_path.exists():
    print("snapshot not found:", snap_path)
    raise SystemExit(2)
with open(snap_path, "r", encoding="utf-8") as fh:
    data = json.load(fh)

first_ex = next(iter(data.keys()))
payload = data[first_ex]
payload.setdefault("ex_id", first_ex)
payload.setdefault("tokens", ["A", "B", "C"])
payload.setdefault("fee", 0.1)

telemetry_path = Path(args.telemetry)
telemetry_path.parent.mkdir(parents=True, exist_ok=True)

print(
    f"Running Bellman-Ford benchmark: iters={args.iters}, snapshot={snap_path}, telemetry={telemetry_path}"
)
start_all = time.time()
written = 0
for i in range(args.iters):
    t0 = time.time()
    res = bf(f"bench_snap_{i}", payload, {})
    dur = time.time() - t0
    entry = {
        "snapshot_id": f"bench_snap_{i}",
        "technique": "bellman_ford",
        "timestamp": int(time.time()),
        "duration_s": dur,
        "results_count": len(res) if res else 0,
    }
    with open(telemetry_path, "a", encoding="utf-8") as tfh:
        tfh.write(json.dumps(entry) + "\n")
        written += 1
    if (i + 1) % 25 == 0:
        elapsed = time.time() - start_all
        print(f"  completed {i+1}/{args.iters} iterations (elapsed {elapsed:.1f}s)")

print(
    f"Done. iterations={args.iters} telemetry_written={written} total_elapsed={time.time()-start_all:.1f}s"
)
