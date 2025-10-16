import time
import json
import sys
import os
from pathlib import Path
from collections import deque


def fetch_binance_tickers():
    try:
        from binance.client import Client as BinanceClient
        client = BinanceClient()
        data = client.get_ticker()
        # Debug: show type and a sample element to determine structure
        try:
            print(f"BINANCE RAW TYPE: {type(data)}; length={len(data) if hasattr(data, '__len__') else 'n/a'}")
            if isinstance(data, (list, tuple)) and data:
                print("BINANCE SAMPLE KEYS:", list(data[0].keys()))
            elif isinstance(data, dict):
                # print first key and value type
                first_k = next(iter(data.keys())) if data else None
                print("BINANCE DICT FIRST_KEY:", first_k, "-> type", type(data.get(first_k)))
        except Exception:
            pass
        tickers = {}
        for entry in data:
            sym = entry.get('symbol')
            # Binance uses 'lastPrice', and provides bidPrice/askPrice
            last = entry.get('lastPrice') or entry.get('price') or entry.get('close')
            bid = entry.get('bidPrice') or entry.get('bid')
            ask = entry.get('askPrice') or entry.get('ask')
            if sym:
                tickers[sym] = {
                    'last': float(last) if last else None,
                    'bid': float(bid) if bid else None,
                    'ask': float(ask) if ask else None,
                }
        return tickers
    except Exception as e:
        print(f"Binance fetch error: {e}")
        return {}

def fetch_okx_tickers():
    try:
        import okx.MarketData as OKXMarket
        api = OKXMarket.MarketAPI()
        data = api.get_tickers(instType="SPOT")
        tickers = {}
        for entry in data.get('data', []):
            sym = entry.get('instId')
            last = entry.get('last')
            bid = entry.get('bidPx')
            ask = entry.get('askPx')
            if sym:
                tickers[sym] = {'last': float(last) if last else None, 'bid': float(bid) if bid else None, 'ask': float(ask) if ask else None}
        return tickers
    except Exception as e:
        print(f"OKX fetch error: {e}")
        return {}

def fetch_bitget_tickers():
    try:
        from bitget import BitgetSync
        api = BitgetSync()
        data = api.public_spot_get_spot_v1_market_tickers()
        # Debug: show structure and sample
        try:
            print(f"BITGET RAW TYPE: {type(data)}")
            if isinstance(data, dict):
                print("BITGET KEYS:", list(data.keys()))
                sample = (data.get('data') or [])[:1]
                print("BITGET SAMPLE:", sample)
        except Exception:
            pass
        tickers = {}
        for entry in data.get('data', []):
            sym = entry.get('symbol')
            # Bitget returns 'close' as last, and 'buyOne'/'sellOne' for top bid/ask
            last = entry.get('close') or entry.get('last') or entry.get('price')
            bid = entry.get('buyOne') or entry.get('bestBid') or entry.get('bid')
            ask = entry.get('sellOne') or entry.get('bestAsk') or entry.get('ask')
            if sym:
                try:
                    tickers[sym] = {
                        'last': float(last) if last else None,
                        'bid': float(bid) if bid else None,
                        'ask': float(ask) if ask else None,
                    }
                except Exception:
                    # fallback: store raw strings if float conversion fails
                    tickers[sym] = {'last': last, 'bid': bid, 'ask': ask}
        return tickers
    except Exception as e:
        print(f"Bitget fetch error: {e}")
        return {}


def fetch_mexc_tickers():
    try:
        from mexc_api.spot import Spot
        client = Spot("", "")
        data = client.market.ticker_price()
        tickers = {}
        for entry in data:
            sym = entry.get('symbol')
            price = entry.get('price')
            if sym and price:
                tickers[sym] = {'last': float(price)}
        return tickers
    except Exception as e:
        print(f"MEXC fetch error: {e}")
        return {}

def fetch_tickers_for_all():
    exchanges = {
        'binance': fetch_binance_tickers,
        'okx': fetch_okx_tickers,
        'bitget': fetch_bitget_tickers,
        'mexc': fetch_mexc_tickers,
    }
    results = {}
    for ex, func in exchanges.items():
        t0 = time.time()
        tickers = func()
        t1 = time.time()
        print(f"DEBUG: {ex} fetched {len(tickers)} tickers.")
        if len(tickers) == 0:
            print(f"DEBUG: {ex} returned 0 tickers! Possible SDK/env issue.")
        results[ex] = (tickers, t1-t0)
    return results


def check_environment():
    """Quick environment sanity checks.

    - Ensure we are running from the arbitraje project (pyproject.toml present).
    - Ensure required SDKs are importable and give actionable guidance if not.
    """
    repo_project_dir = Path(__file__).resolve().parents[1]
    if not (repo_project_dir / "pyproject.toml").exists():
        print("ERROR: It looks like you're not running inside the 'projects/arbitraje' project.")
        print("Recommendation: cd into 'projects/arbitraje' and run the script using Poetry:")
        print("  cd projects/arbitraje")
        print("  poetry install")
        print("  poetry run python scripts/diagnose_ticker_fetch.py")
        sys.exit(2)

    # Try importing the SDKs we use; collect missing ones to show a helpful message
    missing = []
    try:
        import binance  # type: ignore
    except Exception:
        missing.append("python-binance (binance)")
    try:
        import bitget  # type: ignore
    except Exception:
        missing.append("bitget SDK (bitget)")
    try:
        import okx  # type: ignore
    except Exception:
        missing.append("okx SDK (okx)")
    try:
        import mexc_api  # type: ignore
    except Exception:
        missing.append("mexc-api (mexc_api)")

    if missing:
        print("ERROR: The following SDKs are not importable in the current Python environment:")
        for m in missing:
            print(" - ", m)
        print("")
        print("If you are using Poetry for the project, fix by running:")
        print("  cd projects/arbitraje && poetry install && poetry run python scripts/diagnose_ticker_fetch.py")
        print("")
        sys.exit(3)

def count_valid_rates(tickers):
    n_valid = 0
    for t in tickers.values():
        try:
            if (t.get("bid") and float(t.get("bid")) > 0) or (t.get("ask") and float(t.get("ask")) > 0) or (t.get("last") and float(t.get("last")) > 0):
                n_valid += 1
        except Exception:
            pass
    return n_valid

def build_graph(tickers):
    graph = {}
    for sym, t in tickers.items():
        # Support both 'BTC/USDT' and 'BTCUSDT' formats
        if "/" in sym:
            a, b = sym.split("/")
        elif len(sym) >= 6:
            # Try to split at the most likely base/quote boundary (common for Binance, MEXC)
            # Use a list of common quote assets
            QUOTES = ["USDT", "USDC", "BUSD", "TUSD", "FDUSD", "DAI", "BTC", "ETH"]
            found = False
            for q in QUOTES:
                if sym.endswith(q) and len(sym) > len(q):
                    a = sym[:-len(q)]
                    b = q
                    found = True
                    break
            if not found:
                continue
        else:
            continue
        rate = None
        try:
            if t.get("bid") is not None:
                rate = float(t.get("bid"))
            elif t.get("last") is not None:
                rate = float(t.get("last"))
        except Exception:
            rate = None
        if rate is not None and rate > 0:
            graph.setdefault(a, set()).add(b)
            graph.setdefault(b, set())
        try:
            if t.get("ask") is not None:
                ask = float(t.get("ask"))
                if ask:
                    graph.setdefault(b, set()).add(a)
                    graph.setdefault(a, set())
        except Exception:
            pass
    return graph

def connected_components(graph):
    visited = set()
    components = []
    for node in graph:
        if node not in visited:
            comp = set()
            queue = deque([node])
            while queue:
                n = queue.popleft()
                if n in visited:
                    continue
                visited.add(n)
                comp.add(n)
                queue.extend(graph[n] - visited)
            components.append(comp)
    return components


def main():
    all_results = fetch_tickers_for_all()
    diag_all = {}
    for ex, (tickers, fetch_time) in all_results.items():
        n_tickers = len(tickers)
        n_valid = count_valid_rates(tickers)
        graph = build_graph(tickers)
        n_nodes = len(graph)
        n_edges = sum(len(neigh) for neigh in graph.values())
        comps = connected_components(graph)
        n_comps = len(comps)
        largest_comp = max((len(c) for c in comps), default=0)
        diag = {
            "tickers": n_tickers,
            "valid_rates": n_valid,
            "fetch_time_sec": fetch_time,
            "graph_nodes": n_nodes,
            "graph_edges": n_edges,
            "connected_components": n_comps,
            "largest_component_size": largest_comp,
        }
        diag_all[ex] = diag
        print(f"=== {ex.upper()} ===")
        print(json.dumps(diag, indent=2))

    # Save diagnostics
    diag_path = Path(__file__).parent.parent / "artifacts" / "arbitraje" / "fetch_diagnostics.json"
    diag_path.parent.mkdir(parents=True, exist_ok=True)
    with open(diag_path, "w", encoding="utf-8") as f:
        json.dump(diag_all, f, indent=2)

    return diag_all


def cli():
    import argparse

    parser = argparse.ArgumentParser(description="Connector fetch diagnostics for arbitraje")
    parser.add_argument("--no-sim", action="store_true", help="Skip the simulated 10s delay at the end (useful for CI)")
    args = parser.parse_args()

    # Environment check: fail-fast with guidance
    check_environment()

    diag_all = main()

    if not args.no_sim:
        # Simulate slow fetch (optional)
        print("Simulating slow fetch...")
        t0 = time.time()
        time.sleep(10)  # Simulate 10s delay
        t1 = time.time()
        print(f"Simulated fetch time: {t1-t0:.2f}s")


if __name__ == "__main__":
    cli()

if __name__ == "__main__":
    main()
