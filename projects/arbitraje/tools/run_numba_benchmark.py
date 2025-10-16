"""Run the Numba-accelerated Bellman-Ford (POC) if available.

Usage: python run_numba_benchmark.py --iters 50
"""

import argparse
import json
import time
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--iters", type=int, default=50)
parser.add_argument(
    "--snapshot",
    type=str,
    default=str(
        Path(__file__).resolve().parents[1]
        / "artifacts"
        / "arbitraje"
        / "offline_snapshot_synth_large.json"
    ),
)
parser.add_argument(
    "--telemetry",
    type=str,
    default=str(
        Path(__file__).resolve().parents[1]
        / "artifacts"
        / "arbitraje"
        / "techniques_telemetry_numba.log"
    ),
)
args = parser.parse_args()

# import local bf_numba_impl
from bf_numba_impl import (
    build_arrays_from_payload,
    bellman_ford_numba,
    bellman_ford_array,
)

snap_path = Path(args.snapshot)
if not snap_path.exists():
    print("snapshot not found:", snap_path)
    raise SystemExit(2)

with open(snap_path, "r", encoding="utf-8") as fh:
    data = json.load(fh)
first = next(iter(data.keys()))
payload = data[first]

nodes, u_arr, v_arr, w_arr = build_arrays_from_payload(payload)
n = len(nodes)

if bellman_ford_numba is None:
    print("Numba implementation not available in this environment. Exiting.")
    raise SystemExit(1)

telemetry_path = Path(args.telemetry)
telemetry_path.parent.mkdir(parents=True, exist_ok=True)

print(f"Numba available: warming up JIT on n={n}, edges={len(u_arr)}")
# warm-up (first call triggers compilation)
start_w = time.time()
_ = bellman_ford_numba(n, u_arr, v_arr, w_arr)
warm_elapsed = time.time() - start_w
print(f"Warm-up (compile) elapsed: {warm_elapsed:.2f}s")

# run iterations and write telemetry
samples = []
for i in range(args.iters):
    tid = f"numba_bench_{i}"
    t0 = time.time()
    res = bellman_ford_numba(n, u_arr, v_arr, w_arr)
    dur = time.time() - t0
    samples.append(dur * 1000.0)
    entry = {
        "snapshot_id": tid,
        "technique": "bellman_ford_numba",
        "timestamp": int(time.time()),
        "duration_s": dur,
        "results_count": len(res) if res else 0,
    }
    with open(telemetry_path, "a", encoding="utf-8") as tfh:
        tfh.write(json.dumps(entry) + "\n")
    if (i + 1) % 10 == 0:
        print(f"  completed {i+1}/{args.iters}")

samples.sort()


def quantile(sorted_vals, q):
    n = len(sorted_vals)
    pos = q * (n - 1)
    lo = int(pos)
    hi = int(pos) + (1 if pos - lo > 0 else 0)
    if hi >= n:
        hi = n - 1
    if lo == hi:
        return sorted_vals[int(pos)]
    return sorted_vals[lo] + (pos - lo) * (sorted_vals[hi] - sorted_vals[lo])


print(f"Ran {len(samples)} samples (ms)")
print(f"p50: {quantile(samples,0.5):.3f} ms")
print(f"p90: {quantile(samples,0.9):.3f} ms")
print(f"p99: {quantile(samples,0.99):.3f} ms")
print("Done")
