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
    cfg = {
        "techniques": {
            "enabled": ["bellman_ford"],
            "max_workers": 1,
            "telemetry_file": "tech_telemetry.jsonl",
        }
    }
    res = scan_arbitrage("snap-test", payload, cfg)
    print("scan_arbitrage returned len:", len(res) if res else 0)
    try:
        print(json.dumps(res[:5], indent=2))
    except Exception:
        print(res)


if __name__ == "__main__":
    run()
