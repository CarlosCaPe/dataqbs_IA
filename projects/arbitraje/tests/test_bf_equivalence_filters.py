from arbitraje.engine_techniques import scan_arbitrage
from arbitraje import arbitrage_report_ccxt as arc


def make_tickers_with_blacklist():
    t = {
        "A/USDT": {"bid": 1.0, "ask": 1.0, "last": 1.0, "quoteVolume": 1000},
        "B/USDT": {"bid": 1.0, "ask": 1.0, "last": 1.0, "quoteVolume": 1000},
        "C/USDT": {"bid": 1.0, "ask": 1.0, "last": 1.0, "quoteVolume": 1000},
        "A/B": {"bid": 1.02, "ask": 1.0, "last": 1.0, "quoteVolume": 1000},
        "B/C": {"bid": 1.02, "ask": 1.0, "last": 1.0, "quoteVolume": 1000},
        "C/A": {"bid": 1.02, "ask": 1.0, "last": 1.0, "quoteVolume": 1000},
    }
    return t


def test_bf_min_hops_and_blacklist():
    tickers = make_tickers_with_blacklist()
    payload = {
        "ex_id": "testex",
        "quote": "USDT",
        "tokens": ["A", "B", "C"],
        "tickers": tickers,
        "fee": 0.10,
        "min_quote_vol": 0.0,
        "min_net": 0.0,
        "ts": "tst",
        "top": 10,
        "min_hops": 3,
        "blacklist": ["A->B"],
    }
    cfg = {"techniques": {"enabled": ["bellman_ford"], "max_workers": 1}}
    res = scan_arbitrage("snap1", payload, cfg)
    # Because we blacklist A->B, the expected profitable cycle should not be found
    for r in res:
        assert "A->B" not in (r.get("cycle") or "")
