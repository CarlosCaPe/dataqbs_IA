import pickle
import time

from arbitraje.engine_techniques import scan_arbitrage


def make_synthetic_tickers(n_symbols=6):
    # Create simple tickers for currencies A,B,C vs USDT
    tickers = {}
    pairs = ["A/USDT", "B/USDT", "C/USDT", "A/B", "B/C", "C/A"]
    for p in pairs:
        # simple symmetric market
        tickers[p] = {"bid": 1.0, "ask": 1.0, "last": 1.0, "quoteVolume": 1000}
    # make a profitable cycle by boosting A/B and B/C and C/A
    tickers["A/B"]["bid"] = 1.02
    tickers["B/C"]["bid"] = 1.02
    tickers["C/A"]["bid"] = 1.02
    return tickers


def test_scan_arbitrage_stat_tri_and_bf():
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
    cfg = {"techniques": {"enabled": ["stat_tri", "bellman_ford"], "max_workers": 2}}

    res = scan_arbitrage("snap1", payload, cfg)
    # Expect at least one actionable result
    assert isinstance(res, list)
    assert len(res) >= 1

    # measure pickling size/time for payload
    t0p = time.time()
    p = pickle.dumps(payload)
    t1p = time.time()
    size = len(p)
    assert size < 200_000  # payload should be small
    assert (t1p - t0p) < 1.0
