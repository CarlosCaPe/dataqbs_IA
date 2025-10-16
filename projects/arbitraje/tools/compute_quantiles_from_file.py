import json
import sys
from pathlib import Path
from math import floor, ceil

p = (
    Path(sys.argv[1])
    if len(sys.argv) > 1
    else Path(
        "projects/arbitraje/artifacts/arbitraje/techniques_telemetry_synth_after.log"
    )
)
if not p.exists():
    print("file not found", p)
    raise SystemExit(2)
vals = []
with open(p, "r", encoding="utf-8") as fh:
    for l in fh:
        try:
            j = json.loads(l)
            if j.get("technique") == "bellman_ford":
                d = j.get("duration_s")
                if d is not None:
                    vals.append(float(d) * 1000.0)
        except Exception:
            continue
if not vals:
    print("no samples")
    raise SystemExit(1)
vals.sort()


def quantile(sorted_vals, q):
    n = len(sorted_vals)
    pos = q * (n - 1)
    lo = int(floor(pos))
    hi = int(ceil(pos))
    if lo == hi:
        return sorted_vals[int(pos)]
    return sorted_vals[lo] + (pos - lo) * (sorted_vals[hi] - sorted_vals[lo])


print("samples=", len(vals))
print(f"p50: {quantile(vals,0.5):.3f} ms")
print(f"p90: {quantile(vals,0.9):.3f} ms")
print(f"p99: {quantile(vals,0.99):.3f} ms")
