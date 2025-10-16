import json
import math
from pathlib import Path

telemetry = Path(
    r"c:\Users\Lenovo\dataqbs_IA\projects\arbitraje\artifacts\arbitraje\techniques_telemetry.log"
)
if not telemetry.exists():
    print("telemetry file not found:", telemetry)
    raise SystemExit(2)

vals = []
with open(telemetry, "r", encoding="utf-8") as fh:
    for line in fh:
        try:
            j = json.loads(line)
            if j.get("technique") == "bellman_ford":
                d = j.get("duration_s")
                if d is not None:
                    vals.append(float(d) * 1000.0)
        except Exception:
            continue

if not vals:
    print("No bellman_ford durations found in telemetry")
    raise SystemExit(1)

vals.sort()


def quantile(sorted_vals, q):
    n = len(sorted_vals)
    pos = q * (n - 1)
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return sorted_vals[int(pos)]
    return sorted_vals[lo] + (pos - lo) * (sorted_vals[hi] - sorted_vals[lo])


print(f"Found {len(vals)} bellman_ford samples (ms)")
print(f"p50: {quantile(vals,0.5):.1f} ms")
print(f"p90: {quantile(vals,0.9):.1f} ms")
print(f"p99: {quantile(vals,0.99):.1f} ms")

print("\nSample (first 20 sorted):")
for v in vals[:20]:
    print(f"  {v:.1f}ms")

print("\nTop 10:")
for v in vals[-10:]:
    print(f"  {v:.1f}ms")
