"""Analyze BF windows dataset: distributions, percentiles, and plots.

Inputs:
- artifacts/arbitraje/outputs/arbitrage_bf_usdt_ccxt.csv
- artifacts/arbitraje/outputs/arbitrage_bf_simulation_usdt_ccxt.csv
- artifacts/arbitraje/outputs/arbitrage_bf_usdt_persistence.csv (optional)

Outputs (under artifacts/arbitraje/analysis):
- bf_windows_summary.json
- bf_windows_report.md
- histogram_net_bps_est.png
- kde_net_bps_est.png (optional if seaborn available)
"""

from __future__ import annotations
import argparse
import csv
import json
import math
from pathlib import Path
from statistics import mean, median


def load_csv(path: Path) -> list[dict]:
    rows: list[dict] = []
    if not path.exists():
        return rows
    with open(path, "r", encoding="utf-8") as fh:
        rdr = csv.DictReader(fh)
        for r in rdr:
            rows.append(r)
    return rows


def safe_float(x, default=0.0):
    try:
        if x is None or x == "":
            return default
        return float(x)
    except Exception:
        return default


def percentile(sorted_vals: list[float], p: float) -> float:
    if not sorted_vals:
        return 0.0
    n = len(sorted_vals)
    pos = p * (n - 1)
    lo = int(pos)
    hi = min(n - 1, lo + 1)
    if lo == hi:
        return sorted_vals[int(pos)]
    return sorted_vals[lo] + (pos - lo) * (sorted_vals[hi] - sorted_vals[lo])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--outputs-dir",
        default=str(Path("artifacts/arbitraje/outputs").resolve()),
        help="Directory with BF CSV outputs",
    )
    parser.add_argument(
        "--analysis-dir",
        default=str(Path("artifacts/arbitraje/analysis").resolve()),
        help="Where to write analysis artifacts",
    )
    parser.add_argument(
        "--field",
        default="net_bps_est",
        help="Field to analyze for distributions (default: net_bps_est)",
    )
    args = parser.parse_args()

    outdir = Path(args.outputs_dir)
    andir = Path(args.analysis_dir)
    andir.mkdir(parents=True, exist_ok=True)

    bf_csv = outdir / "arbitrage_bf_usdt_ccxt.csv"
    sim_csv = outdir / "arbitrage_bf_simulation_usdt_ccxt.csv"
    pers_csv = outdir / "arbitrage_bf_usdt_persistence.csv"

    bf_rows = load_csv(bf_csv)
    sim_rows = load_csv(sim_csv)
    pers_rows = load_csv(pers_csv)

    def collect(vals):
        arr = [safe_float(r.get(args.field)) for r in vals]
        arr = [x for x in arr if not math.isnan(x)]
        arr.sort()
        return arr

    bf_vals = collect(bf_rows)
    sim_vals = collect(sim_rows)

    def describe(arr):
        return {
            "count": len(arr),
            "mean": mean(arr) if arr else 0.0,
            "median": median(arr) if arr else 0.0,
            "p10": percentile(arr, 0.10) if arr else 0.0,
            "p25": percentile(arr, 0.25) if arr else 0.0,
            "p50": percentile(arr, 0.50) if arr else 0.0,
            "p75": percentile(arr, 0.75) if arr else 0.0,
            "p90": percentile(arr, 0.90) if arr else 0.0,
            "p95": percentile(arr, 0.95) if arr else 0.0,
            "p99": percentile(arr, 0.99) if arr else 0.0,
            ">0_count": sum(1 for x in arr if x > 0),
            ">=5bps_count": sum(1 for x in arr if x >= 5.0),
            ">=10bps_count": sum(1 for x in arr if x >= 10.0),
        }

    summary = {
        "field": args.field,
        "bf": describe(bf_vals),
        "sim": describe(sim_vals),
        "persistence_rows": len(pers_rows),
    }

    with open(andir / "bf_windows_summary.json", "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2)

    # Try plotting if matplotlib is available
    plot_ok = False
    try:
        import matplotlib.pyplot as plt

        def plot_hist(vals, title, fname):
            if not vals:
                return
            plt.figure(figsize=(8, 4))
            plt.hist(vals, bins=60, color="#4c78a8", alpha=0.85)
            plt.title(title)
            plt.xlabel(args.field)
            plt.ylabel("count")
            plt.grid(True, alpha=0.25)
            plt.tight_layout()
            plt.savefig(andir / fname)
            plt.close()

        plot_hist(
            bf_vals,
            "BF windows distribution (net_bps_est)",
            "histogram_net_bps_est.png",
        )
        plot_ok = True

        # Optional KDE if seaborn exists
        try:
            import seaborn as sns  # type: ignore

            plt.figure(figsize=(8, 4))
            if bf_vals:
                sns.kdeplot(bf_vals, fill=True, color="#4c78a8")
                plt.title("BF windows KDE (net_bps_est)")
                plt.xlabel(args.field)
                plt.grid(True, alpha=0.25)
                plt.tight_layout()
                plt.savefig(andir / "kde_net_bps_est.png")
                plt.close()
        except Exception:
            pass

    except Exception:
        plot_ok = False

    # Write Markdown report
    def fmt(d: dict) -> str:
        return (
            f"count: {d['count']}, mean: {d['mean']:.3f}, median: {d['median']:.3f}, "
            f"p10: {d['p10']:.3f}, p25: {d['p25']:.3f}, p50: {d['p50']:.3f}, "
            f"p75: {d['p75']:.3f}, p90: {d['p90']:.3f}, p95: {d['p95']:.3f}, p99: {d['p99']:.3f}, "
            f">0: {d['>0_count']}, >=5bps: {d['>=5bps_count']}, >=10bps: {d['>=10bps_count']}"
        )

    lines = [
        "# BF Windows Report",
        "",
        f"Field analyzed: {args.field}",
        "",
        "## Summary",
        "",
        "- BF: " + fmt(summary["bf"]),
        "- SIM: " + fmt(summary["sim"]),
        f"- Persistence rows: {summary['persistence_rows']}",
        "",
    ]
    if plot_ok:
        lines += [
            "## Distributions",
            "",
            "![Histogram](histogram_net_bps_est.png)",
            "",
            "![KDE](kde_net_bps_est.png)",
            "",
        ]

    with open(andir / "bf_windows_report.md", "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))

    print(json.dumps(summary, indent=2))
    print("Wrote report to", andir)


if __name__ == "__main__":
    main()
