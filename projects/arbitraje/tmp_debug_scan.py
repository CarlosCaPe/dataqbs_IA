import json
from arbitraje.engine_techniques import scan_arbitrage


def make_synthetic_tickers():
    tickers = {}
    pairs = ["A/USDT", "B/USDT", "C/USDT", "A/B", "B/C", "C/A"]
    for p in pairs:
        tickers[p] = {"bid": 1.0, "ask": 1.0, "last": 1.0, "quoteVolume": 1000}
    tickers["A/B"]["bid"] = 1.02
    tickers["B/C"]["bid"] = 1.02
    tickers["C/A"]["bid"] = 1.02
    return tickers


def main():
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
    cfg_inline = {
        "techniques": {"enabled": ["bellman_ford"], "inline": ["bellman_ford"]}
    }
    print("Running scan_arbitrage INLINE with payload size", len(json.dumps(payload)))
    res_inline = scan_arbitrage("snap-debug-inline", payload, cfg_inline)
    print("INLINE Result count:", len(res_inline))
    print(json.dumps(res_inline, indent=2))

    cfg_pool = {"techniques": {"enabled": ["bellman_ford"], "max_workers": 1}}
    print(
        "\nRunning scan_arbitrage POOL (ProcessPoolExecutor) with payload size",
        len(json.dumps(payload)),
    )
    res_pool = scan_arbitrage("snap-debug-pool", payload, cfg_pool)
    print("POOL Result count:", len(res_pool))
    print(json.dumps(res_pool, indent=2))


if __name__ == "__main__":
    main()
