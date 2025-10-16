import time
import json
from pathlib import Path
from collections import deque


def fetch_binance_tickers():
    try:
        from binance_sdk_spot.spot import Spot
        spot = Spot()
        # This returns a dict with 'symbols' key
        data = spot.rest_api.ticker_price()
        # Convert to {symbol: {last: price}} format
        tickers = {}
        for entry in data:
            sym = entry.get('symbol')
            price = entry.get('price')
            if sym and price:
                tickers[sym] = {'last': float(price)}
        return tickers
    except Exception as e:
        print(f"Binance fetch error: {e}")
        return {}

def fetch_okx_tickers():
    try:
        from okx.MarketData import MarketAPI
        api = MarketAPI()
        # Get all spot tickers
        data = api.get_tickers('SPOT')
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
        from bitget.bitget_api import Bitget
        api = Bitget()
        data = api.get_tickers('spot')
        tickers = {}
        for entry in data.get('data', []):
            sym = entry.get('symbol')
            last = entry.get('last')
            bid = entry.get('bestBid')
            ask = entry.get('bestAsk')
            if sym:
                tickers[sym] = {'last': float(last) if last else None, 'bid': float(bid) if bid else None, 'ask': float(ask) if ask else None}
        return tickers
    except Exception as e:
        print(f"Bitget fetch error: {e}")
        return {}

# MEXC is a Node.js/TypeScript SDK, so Python cannot import it directly. Skipping MEXC for now.

def fetch_tickers_for_all():
    exchanges = {
        'binance': fetch_binance_tickers,
        'okx': fetch_okx_tickers,
        'bitget': fetch_bitget_tickers,
        # 'mexc': fetch_mexc_tickers, # Not implemented in Python
    }
    results = {}
    for ex, func in exchanges.items():
        t0 = time.time()
        tickers = func()
        t1 = time.time()
        results[ex] = (tickers, t1-t0)
    return results

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
        if "/" not in sym:
            continue
        a, b = sym.split("/")
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

    # Simulate slow fetch (optional)
    print("Simulating slow fetch...")
    t0 = time.time()
    time.sleep(10)  # Simulate 10s delay
    t1 = time.time()
    print(f"Simulated fetch time: {t1-t0:.2f}s")

if __name__ == "__main__":
    main()
