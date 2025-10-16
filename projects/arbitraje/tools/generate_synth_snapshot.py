"""Generate a synthetic offline snapshot for Bellman-Ford benchmarking.

Usage: python generate_synth_snapshot.py --tokens 120 --conn 10 --out path
"""

import argparse
import json
from pathlib import Path
import random

parser = argparse.ArgumentParser()
parser.add_argument("--tokens", type=int, default=120)
parser.add_argument(
    "--conn", type=int, default=10, help="number of forward connections per token"
)
parser.add_argument(
    "--out",
    type=str,
    default=str(
        Path(__file__).resolve().parents[1]
        / "artifacts"
        / "arbitraje"
        / "offline_snapshot_synth_large.json"
    ),
)
args = parser.parse_args()

N = args.tokens
K = args.conn
out = Path(args.out)
out.parent.mkdir(parents=True, exist_ok=True)

random.seed(42)

tokens = [f"T{i:03d}" for i in range(N)]
# Build tickers: for each i, connect to next K tokens (wrap-around)
tickers = {}
markets = {}
for i, t in enumerate(tokens):
    for j in range(1, K + 1):
        v = tokens[(i + j) % N]
        sym = f"{t}/{v}"
        # create a rate close to 1.0 with small random deviations but ensure >0
        rate = 1.0 + (random.random() - 0.5) * 0.02
        # bid slightly lower than last, ask slightly higher
        last = round(rate, 6)
        bid = round(rate * (1.0 - 0.0005), 6)
        ask = round(rate * (1.0 + 0.0005), 6)
        tickers[sym] = {
            "bid": bid,
            "ask": ask,
            "last": last,
            "quoteVolume": round(random.uniform(1000, 5000), 2),
        }
        markets[sym] = {"base": t, "quote": v, "active": True}

# put everything under a single synthetic exchange
snap = {
    "synthex": {"markets": markets, "tickers": tickers, "tokens": tokens, "fee": 0.10}
}
with open(out, "w", encoding="utf-8") as fh:
    json.dump(snap, fh)
print("wrote snapshot:", out)
print("tokens:", N, "connections per token:", K)
