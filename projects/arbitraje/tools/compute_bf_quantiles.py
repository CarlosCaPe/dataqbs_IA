import re
import math
from pathlib import Path

log_path = Path(
    r"c:\Users\Lenovo\dataqbs_IA\artifacts\arbitraje\logs\arbitraje_ccxt.log"
)
if not log_path.exists():
    print(f"ERROR: log not found: {log_path}")
    raise SystemExit(2)

text = log_path.read_text(encoding="utf-8")
# try to find patterns like total=1946.4ms
vals = [float(x) for x in re.findall(r"total=(\d+(?:\.\d+)?)ms", text)]
# fallback: sometimes whitespace or other separators
if not vals:
    vals = [float(x) for x in re.findall(r"total\s*=\s*(\d+(?:\.\d+)?)\s*ms", text)]

if not vals:
    print(
        "No 'total=...ms' values found in log."
        " Make sure the log contains BF timing lines."
    )
    raise SystemExit(1)

vals.sort()


def quantile(sorted_vals, q):
    n = len(sorted_vals)
    if n == 0:
        return None
    pos = q * (n - 1)
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return sorted_vals[int(pos)]
    return sorted_vals[lo] + (pos - lo) * (sorted_vals[hi] - sorted_vals[lo])


p50 = quantile(vals, 0.50)
p90 = quantile(vals, 0.90)
p99 = quantile(vals, 0.99)

print(f"Found {len(vals)} BF total timings (ms)")
print(f"p50: {p50:.1f} ms")
print(f"p90: {p90:.1f} ms")
print(f"p99: {p99:.1f} ms")
print()
print("Sample values (sorted, up to 20):")
for v in vals[:20]:
    print(f"  {v:.1f}ms")

# Also print the top 10 largest
print()
print("Top 10 largest:")
for v in vals[-10:]:
    print(f"  {v:.1f}ms")
