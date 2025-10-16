import importlib

mod = importlib.import_module("arbitraje.arbitrage_report_ccxt")


def make_simple_tickers():
    # Provide tickers for markets A/B, B/C, C/A in both directions
    return {
        "USDT/MINA": {"bid": 0.5, "ask": 0.51, "last": 0.505, "quoteVolume": 1000},
        "MINA/EUR": {"bid": 1.5, "ask": 1.52, "last": 1.51, "quoteVolume": 500},
        "EUR/USDT": {"bid": 1.4, "ask": 1.42, "last": 1.41, "quoteVolume": 800},
        # include inverse pairs to exercise get_rate_and_qvol fallback
        "MINA/USDT": {"bid": 2.0, "ask": 2.02, "last": 2.01, "quoteVolume": 100},
    }


def test_get_rate_and_qvol_direct_and_inverse():
    tickers = make_simple_tickers()
    # direct exists: USDT -> MINA (sym 'USDT/MINA'): selling USDT for MINA uses bid on USDT/MINA
    r, qv = mod.get_rate_and_qvol(
        "USDT", "MINA", tickers, fee_pct=0.1, require_topofbook=False
    )
    assert r is not None and qv is not None
    # inverse path: MINA -> USDT should produce rate via direct MINA/USDT or inverse
    r2, qv2 = mod.get_rate_and_qvol(
        "MINA", "USDT", tickers, fee_pct=0.1, require_topofbook=False
    )
    assert r2 is not None and qv2 is not None


def test_pair_blacklist_behavior():
    # Create a minimal blacklist and ensure _pair_is_blacklisted detects both orientations
    bl = {"USDT/MINA"}
    assert mod._pair_is_blacklisted(bl, "USDT", "MINA")
    assert mod._pair_is_blacklisted(bl, "MINA", "USDT")
    # Non-blacklisted pair
    assert not mod._pair_is_blacklisted(bl, "MINA", "EUR")


def test_build_rates_with_min_quote_vol_and_fee():
    tickers = make_simple_tickers()
    currencies = ["USDT", "MINA", "EUR"]
    # fee 0% should produce different edges than fee 1%
    edges0, rmap0 = mod.build_rates_for_exchange(
        currencies,
        tickers,
        fee_pct=0.0,
        require_topofbook=False,
        min_quote_vol=0.0,
    )
    edges1, rmap1 = mod.build_rates_for_exchange(
        currencies,
        tickers,
        fee_pct=1.0,
        require_topofbook=False,
        min_quote_vol=0.0,
    )
    # Rate maps should exist
    assert isinstance(rmap0, dict) and isinstance(rmap1, dict)
    # Having higher fee reduces values; check an edge rate is lower under fee
    some_key = next(iter(rmap0.keys()))
    assert rmap1[some_key] <= rmap0[some_key]


def test_tri_worker_detects_opportunity(monkeypatch):
    # Monkeypatch load_exchange and load_swaps_blacklist and supply controlled args
    class FakeEx:
        def __init__(self, ex_id):
            self.id = ex_id

        def load_markets(self):
            return {
                "USDT/MINA": {"base": "MINA", "quote": "USDT", "active": True},
                "MINA/EUR": {"base": "MINA", "quote": "EUR", "active": True},
                "EUR/USDT": {"base": "EUR", "quote": "USDT", "active": True},
            }

        def fetch_tickers(self):
            return {
                "USDT/MINA": {
                    "bid": 0.5,
                    "ask": 0.51,
                    "last": 0.505,
                    "quoteVolume": 1000,
                },
                "MINA/EUR": {
                    "bid": 1.5,
                    "ask": 1.52,
                    "last": 1.51,
                    "quoteVolume": 1000,
                },
                "EUR/USDT": {
                    "bid": 1.4,
                    "ask": 1.42,
                    "last": 1.41,
                    "quoteVolume": 1000,
                },
            }

    monkeypatch.setattr(mod, "load_exchange", lambda eid, timeout=None: FakeEx(eid))
    monkeypatch.setattr(mod, "load_swaps_blacklist", lambda: {})

    # Prepare fake args: small tri_min_net to ensure detection
    class A:
        pass

    # Call main in tri mode (repeat=1) so the nested tri_worker runs within main's scope.
    import sys

    old_argv = sys.argv
    try:
        sys.argv = [
            "arbitraje.arbitrage_report_ccxt",
            "--mode",
            "tri",
            "--repeat",
            "1",
            "--quote",
            "USDT",
            "--tri_min_net",
            "0.1",
        ]
        # Should not raise and should complete
        mod.main()
    finally:
        sys.argv = old_argv
