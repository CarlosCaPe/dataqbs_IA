import json
from concurrent.futures import ProcessPoolExecutor
from arbitraje.engine_techniques import _tech_bellman_ford


def make_synthetic_tickers():
    tickers = {}
    pairs = ["A/USDT", "B/USDT", "C/USDT", "A/B", "B/C", "C/A"]
    for p in pairs:
        tickers[p] = {"bid": 1.0, "ask": 1.0, "last": 1.0, "quoteVolume": 1000}
    tickers["A/B"]["bid"] = 1.02
    tickers["B/C"]["bid"] = 1.02
    tickers["C/A"]["bid"] = 1.02
    return tickers


def run():
    tickers = make_synthetic_tickers()
    payload = {
        "ex_id": "testex",
        "quote": "USDT",
        "tokens": ["A", "B", "C"],
        "tickers": tickers,
        "fee": 0.10,
        "min_quote_vol": 0.0,
        "min_net": 0.0,
        "ts": "tst",
    }
    pw = {
        "ex_id": payload.get("ex_id"),
        "ts": payload.get("ts"),
        "tokens": payload.get("tokens"),
        "tickers": payload.get("tickers"),
        "fee": float(payload.get("fee") or 0.0),
    }
    with ProcessPoolExecutor(max_workers=1) as p:
        fut = p.submit(_tech_bellman_ford, "snap-pool-test", json.dumps(pw), {})
        res = fut.result(timeout=10)
        print("Pool returned:", type(res), len(res) if res else 0)
        try:
            print(json.dumps(res[:5], indent=2))
        except Exception:
            print(res)


if __name__ == "__main__":
    run()
