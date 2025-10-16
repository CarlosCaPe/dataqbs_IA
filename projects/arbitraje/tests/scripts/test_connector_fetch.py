"""
Test script to verify that each connector (Binance, Bitget, OKX, MEXC) can fetch tickers and does not return empty data.
Run with: poetry run python tests/scripts/test_connector_fetch.py
"""
import sys

CONNECTORS = {}

# Binance
try:
    from binance.client import Client as BinanceClient
    CONNECTORS['binance'] = BinanceClient()
except Exception as e:
    print(f"Binance import error: {e}", file=sys.stderr)

# Bitget
try:
    from bitget import BitgetSync
    CONNECTORS['bitget'] = BitgetSync()
except Exception as e:
    print(f"Bitget import error: {e}", file=sys.stderr)

# OKX
try:
    import okx.MarketData as OKXMarket
    CONNECTORS['okx'] = OKXMarket.MarketAPI()
except Exception as e:
    print(f"OKX import error: {e}", file=sys.stderr)

# MEXC
try:
    from mexc_api.spot import Spot
    CONNECTORS['mexc'] = Spot("", "")
except Exception as e:
    print(f"MEXC import error: {e}", file=sys.stderr)
def test_fetch_tickers():
    results = {}
    # Binance
    if 'binance' in CONNECTORS:
        try:
            tickers = CONNECTORS['binance'].get_ticker()
            results['binance'] = len(tickers)
        except Exception as e:
            print(f"Binance fetch error: {e}", file=sys.stderr)
            results['binance'] = 0
    # Bitget
    if 'bitget' in CONNECTORS:
        try:
            tickers = CONNECTORS['bitget'].public_spot_get_spot_v1_market_tickers()
            results['bitget'] = len(tickers.get('data', []))
        except Exception as e:
            print(f"Bitget fetch error: {e}", file=sys.stderr)
            results['bitget'] = 0
    # OKX
    if 'okx' in CONNECTORS:
        try:
            tickers = CONNECTORS['okx'].get_tickers(instType="SPOT")
            results['okx'] = len(tickers.get('data', []))
        except Exception as e:
            print(f"OKX fetch error: {e}", file=sys.stderr)
            results['okx'] = 0
    # MEXC
    if 'mexc' in CONNECTORS:
        try:
            tickers = CONNECTORS['mexc'].market.ticker_price()
            results['mexc'] = len(tickers)
        except Exception as e:
            print(f"MEXC fetch error: {e}", file=sys.stderr)
            results['mexc'] = 0
    print("Connector ticker counts:", results)
    for name, count in results.items():
        if count == 0:
            print(f"ERROR: {name} returned 0 tickers!", file=sys.stderr)
        else:
            print(f"{name}: {count} tickers fetched.")

if __name__ == "__main__":
    test_fetch_tickers()
