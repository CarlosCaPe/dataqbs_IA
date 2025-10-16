#!/usr/bin/env python3
"""Benchmark engine_techniques.scan_arbitrage with synthetic snapshots.

Generates small/medium/large snapshots and runs scan_arbitrage with several
config permutations (max_workers, fallback_timeout). Outputs CSV to
artifacts/arbitraje/bench_techniques.csv and prints a short summary.
"""
from __future__ import annotations

import csv
import os
import random
import time
from typing import Dict

from arbitraje.engine_techniques import scan_arbitrage


def make_snapshot(num_tokens: int, seed: int = 42) -> Dict:
    random.seed(seed + num_tokens)
    tokens = [f"T{i}" for i in range(num_tokens)]
    quote = "USDT"
    tickers: Dict[str, Dict] = {}

    # create a connected ring with some extra random edges
    for i in range(len(tokens)):
        a = tokens[i]
        b = tokens[(i + 1) % len(tokens)]
        rate = 1.0 + random.uniform(-0.01, 0.01)
        tickers[f"{a}/{b}"] = {
            "bid": rate,
            "ask": 1.0 / rate,
            "last": rate,
            "quoteVolume": random.uniform(100, 10000),
        }

    # add cross edges to create more triangles
    for _ in range(max(0, num_tokens // 5)):
        a = random.choice(tokens)
        b = random.choice(tokens)
        if a == b:
            continue
        rate = 1.0 + random.uniform(-0.02, 0.02)
        tickers[f"{a}/{b}"] = {
            "bid": rate,
            "ask": 1.0 / rate,
            "last": rate,
            "quoteVolume": random.uniform(10, 5000),
        }

    payload = {
        "ex_id": "bench-ex",
        "quote": quote,
        "tokens": tokens,
        "tickers": tickers,
        "fee": 0.1,
        "min_net": 0.0,
        "min_quote_vol": 0.0,
        "ts": int(time.time()),
    }
    return payload


def ensure_artifacts_dir():
    out = os.path.join(os.getcwd(), "artifacts", "arbitraje")
    os.makedirs(out, exist_ok=True)
    return out


def run_bench():
    out_dir = ensure_artifacts_dir()
    csv_path = os.path.join(out_dir, "bench_techniques.csv")
    sizes = {"small": 10, "medium": 40, "large": 100}
    worker_options = [1, 2, 4]
    timeout_options = [2.0, 8.0]
    techniques = ["bellman_ford", "stat_tri"]

    rows = []
    for name, ntoks in sizes.items():
        payload = make_snapshot(ntoks)
        for maxw in worker_options:
            for ft in timeout_options:
                cfg = {
                    "techniques": {
                        "enabled": techniques,
                        "max_workers": maxw,
                        "fallback_timeout": ft,
                    }
                }
                # warmup
                _ = scan_arbitrage("warmup", payload, cfg)
                t0 = time.time()
                res = scan_arbitrage(f"bench-{name}-{maxw}-{ft}", payload, cfg)
                t1 = time.time()
                elapsed = t1 - t0
                rows.append(
                    {
                        "size": name,
                        "tokens": ntoks,
                        "max_workers": maxw,
                        "fallback_timeout": ft,
                        "elapsed_s": round(elapsed, 4),
                        "results": len(res),
                    }
                )
                print(
                    (
                        f"size={name:6} tokens={ntoks:4} workers={maxw} "
                        f"timeout={ft:4.1f}s -> {len(res)} results in {elapsed:.3f}s"
                    )
                )

    # write CSV
    with open(csv_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "size",
                "tokens",
                "max_workers",
                "fallback_timeout",
                "elapsed_s",
                "results",
            ],
        )
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

    print(f"Wrote results to {csv_path}")


if __name__ == "__main__":
    run_bench()
