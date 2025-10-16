"""Small utility to parse newline-delimited JSON telemetry files and compute simple stats.

Usage:
    python tools/parse_telemetry.py --file artifacts/arbitraje/telemetry_before.log

Outputs p50/p90/p99 for `duration_s` fields and reports `fallback_count` from scan summaries.
Exit code 1 when thresholds exceeded (args --p99-threshold-ms, --fallback-threshold).
"""

from __future__ import annotations

import argparse
import json
import math
from statistics import median
from typing import List


def percentile(data: List[float], p: float) -> float:
    if not data:
        return 0.0
    data = sorted(data)
    k = (len(data) - 1) * (p / 100.0)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return data[int(k)]
    d0 = data[int(f)] * (c - k)
    d1 = data[int(c)] * (k - f)
    return d0 + d1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True, help="newline JSON telemetry file")
    ap.add_argument("--p99-threshold-ms", type=float, default=1000.0)
    ap.add_argument("--fallback-threshold", type=int, default=3)
    args = ap.parse_args()

    durations = []
    fallback_counts = []
    try:
        with open(args.file, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except Exception:
                    continue
                if "duration_s" in obj:
                    try:
                        durations.append(float(obj.get("duration_s") or 0.0) * 1000.0)
                    except Exception:
                        pass
                # some summaries include telemetry.fallback_count
                if obj.get("telemetry") and isinstance(obj.get("telemetry"), dict):
                    fc = obj.get("telemetry").get("fallback_count")
                    if fc is not None:
                        try:
                            fallback_counts.append(int(fc))
                        except Exception:
                            pass
                # also allow standalone telemetry lines with fallback_count
                if obj.get("fallback_count") is not None:
                    try:
                        fallback_counts.append(int(obj.get("fallback_count")))
                    except Exception:
                        pass
    except FileNotFoundError:
        print(f"File not found: {args.file}")
        raise SystemExit(2)

    p50 = percentile(durations, 50)
    p90 = percentile(durations, 90)
    p99 = percentile(durations, 99)
    total_fallbacks = sum(fallback_counts)

    print(
        f"samples={len(durations)} p50_ms={p50:.3f} p90_ms={p90:.3f} p99_ms={p99:.3f} fallbacks={total_fallbacks}"
    )

    bad = False
    if p99 >= args.p99_threshold_ms:
        print(f"ALERT: p99 {p99:.1f}ms >= threshold {args.p99_threshold_ms}ms")
        bad = True
    if total_fallbacks >= args.fallback_threshold:
        print(
            f"ALERT: fallback_count {total_fallbacks} >= threshold {args.fallback_threshold}"
        )
        bad = True

    if bad:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
