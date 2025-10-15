import types
import builtins
import argparse
import importlib
import pytest


class FakeExchange:
    def __init__(self, ex_id="fake"):
        self.id = ex_id

    def load_markets(self):
        # minimal markets with three currencies including QUOTE
        return {
            "USDT/MINA": {"base": "MINA", "quote": "USDT", "active": True},
            "MINA/EUR": {"base": "MINA", "quote": "EUR", "active": True},
            "EUR/USDT": {"base": "EUR", "quote": "USDT", "active": True},
        }

    def fetch_tickers(self):
        # return last prices that make one triangular profitable
        return {
            "USDT/MINA": {"last": 0.5, "bid": 0.5, "ask": 0.51, "quoteVolume": 1000},
            "MINA/EUR": {"last": 1.5, "bid": 1.5, "ask": 1.52, "quoteVolume": 1000},
            "EUR/USDT": {"last": 1.4, "bid": 1.4, "ask": 1.42, "quoteVolume": 1000},
        }


@pytest.mark.parametrize("quote", ["USDT"]) 
def test_smoke_tri_monkeypatched(monkeypatch, quote):
    # Import the module under test
    mod = importlib.import_module("arbitraje.arbitrage_report_ccxt")

    # Monkeypatch load_exchange used by the module to return our fake exchange
    def fake_load_exchange(ex_id, timeout=None):
        return FakeExchange(ex_id=ex_id)

    monkeypatch.setattr(mod, "load_exchange", fake_load_exchange)

    # Monkeypatch swaps_blacklist_map to empty to avoid filtering
    monkeypatch.setattr(mod, "load_swaps_blacklist", lambda: {})

    # Provide minimal args using the module's parser defaults but override mode/repeat
    parser = argparse.ArgumentParser()
    # The real module uses a global parser built in main(); we will call main with env args
    test_args = ["--mode", "tri", "--repeat", "1", "--quote", quote]

    # Run main via subprocess-like invocation by setting sys.argv
    import sys
    old_argv = sys.argv
    try:
        sys.argv = ["arbitraje.arbitrage_report_ccxt"] + test_args
        mod.main()
    finally:
        sys.argv = old_argv
