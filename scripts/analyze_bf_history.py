import argparse
import os
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

SIM_RX = re.compile(
    r"^\[SIM\] it#(?P<it>\d+) @(?P<ex>\w+)\s+USDT pick .* net (?P<net>[\d\.]+)% \| USDT (?P<u0>[\d\.]+) -> (?P<u1>[\d\.]+) \(\+(?P<delta>[\d\.]+)\)"
)
ITER_TS_RX = re.compile(
    r"^\[BF\] Iteración \d+\/\d+ @ (?P<ts>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+\+\d{2}:\d{2})$"
)


def quantile(sorted_vals: List[float], q: float) -> float:
    if not sorted_vals:
        return 0.0
    if q <= 0:
        return sorted_vals[0]
    if q >= 1:
        return sorted_vals[-1]
    idx = q * (len(sorted_vals) - 1)
    lo = int(idx)
    hi = min(lo + 1, len(sorted_vals) - 1)
    frac = idx - lo
    return sorted_vals[lo] * (1 - frac) + sorted_vals[hi] * frac


def parse_history(path: str) -> Tuple[List[Dict[str, Any]], float]:
    trades: List[Dict[str, Any]] = []
    first_ts = None
    last_ts = None

    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.rstrip("\n")
                m = SIM_RX.match(line)
                if m:
                    trades.append(
                        {
                            "it": int(m.group("it")),
                            "ex": m.group("ex"),
                            "net": float(m.group("net")),
                            "u0": float(m.group("u0")),
                            "u1": float(m.group("u1")),
                            "delta": float(m.group("delta")),
                        }
                    )
                    continue

                tsm = ITER_TS_RX.match(line)
                if tsm:
                    ts = tsm.group("ts")
                    # ISO 8601 with offset
                    try:
                        dt = datetime.fromisoformat(ts)
                    except Exception:
                        # Fallback: strip colon in offset if needed
                        if ts[-3] == ":":
                            ts2 = ts[:-3] + ts[-2:]
                            dt = datetime.strptime(ts2, "%Y-%m-%dT%H:%M:%S.%f%z")
                        else:
                            raise
                    if first_ts is None:
                        first_ts = dt
                    last_ts = dt
    except FileNotFoundError:
        print(f"File not found: {path}", file=sys.stderr)
        return [], 0.0

    hours = 0.0
    if first_ts and last_ts:
        # Normalize to aware datetimes
        if first_ts.tzinfo is None:
            first_ts = first_ts.replace(tzinfo=timezone.utc)
        if last_ts.tzinfo is None:
            last_ts = last_ts.replace(tzinfo=timezone.utc)
        hours = (last_ts - first_ts).total_seconds() / 3600.0

    return trades, hours


def summarize(trades: List[Dict[str, Any]], hours: float) -> List[Dict[str, Any]]:
    by_ex: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
        "nets": [],
        "sum_delta": 0.0,
        "sum_u0": 0.0,
        "n": 0,
    })

    for t in trades:
        ex = t["ex"]
        by_ex[ex]["nets"].append(t["net"])
        by_ex[ex]["sum_delta"] += t["delta"]
        by_ex[ex]["sum_u0"] += t["u0"]
        by_ex[ex]["n"] += 1

    out_rows: List[Dict[str, Any]] = []
    for ex, agg in by_ex.items():
        nets = sorted(agg["nets"])  # ascending
        n = agg["n"]
        avg = sum(nets) / n if n else 0.0
        med = quantile(nets, 0.5)
        p95 = quantile(nets, 0.95)
        per_hour = (n / hours) if hours > 0 else 0.0
        weighted_net_pct = 100.0 * (agg["sum_delta"] / agg["sum_u0"]) if agg["sum_u0"] > 0 else 0.0

        out_rows.append({
            "exchange": ex,
            "trades": n,
            "per_hour": round(per_hour, 2),
            "avg_net_pct": round(avg, 4),
            "median_net_pct": round(med, 4),
            "p95_net_pct": round(p95, 4),
            "weighted_net_pct": round(weighted_net_pct, 4),
            "total_delta": round(agg["sum_delta"], 4),
            "sum_u0": round(agg["sum_u0"], 4),
        })

    out_rows.sort(key=lambda r: r["trades"], reverse=True)
    return out_rows


def write_csv(rows: List[Dict[str, Any]], out_path: str) -> None:
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    headers = [
        "exchange",
        "trades",
        "per_hour",
        "avg_net_pct",
        "median_net_pct",
        "p95_net_pct",
        "weighted_net_pct",
        "total_delta",
        "sum_u0",
    ]
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(",".join(headers) + "\n")
        for r in rows:
            f.write(",".join(str(r[h]) for h in headers) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize BF simulation history per exchange")
    parser.add_argument(
        "--history",
        default=os.path.join("artifacts", "arbitraje", "logs", "bf_history.txt"),
        help="Path to bf_history.txt",
    )
    parser.add_argument(
        "--out",
        default=os.path.join("artifacts", "arbitraje", "outputs", "bf_sim_summary.csv"),
        help="Output CSV path",
    )
    args = parser.parse_args()

    trades, hours = parse_history(args.history)
    if not trades:
        print("No trades found.")
        return 1

    rows = summarize(trades, hours)
    write_csv(rows, args.out)

    print(f"Parsed {len(trades)} trades across {hours:.2f} hours. Summary written to: {args.out}")
    # Pretty print top few
    for r in rows[:10]:
        print(
            f"- {r['exchange']}: trades={r['trades']}, per_hour={r['per_hour']}, "
            f"avg={r['avg_net_pct']}%, median={r['median_net_pct']}%, p95={r['p95_net_pct']}%, "
            f"weighted_net={r['weighted_net_pct']}%"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
