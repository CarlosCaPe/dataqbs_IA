import json
import pathlib
from pprint import pprint
from arbitraje.engine_techniques import _tech_bellman_ford
import ccxt

def fetch_ccxt_tickers(ex_name):
    ex_class = getattr(ccxt, ex_name, None)
    if not ex_class:
        print(f"Exchange {ex_name} not found in ccxt.")
        return None, None
    ex = ex_class()
    try:
        markets = ex.load_markets()
        tickers = ex.fetch_tickers()
    except Exception as e:
        print(f"Error loading markets/tickers for {ex_name}: {e}")
        return None, None
    return markets, tickers

def build_graph_from_tickers(tickers):
    edges = []
    tokens = set()
    for sym, t in tickers.items():
        if '/' not in sym:
            continue
        a, b = sym.split('/')
        tokens.add(a)
        tokens.add(b)
        bid = t.get('bid')
        ask = t.get('ask')
        if bid is not None:
            edges.append((a, b, bid))
        if ask is not None and ask > 0:
            edges.append((b, a, 1.0/ask))
    return list(tokens), edges

def main():
    exchanges = ['binance', 'bitget', 'mexc']
    for ex_name in exchanges:
        print(f"\n=== {ex_name.upper()} ===")
        markets, tickers = fetch_ccxt_tickers(ex_name)
        if not tickers:
            print("No tickers found.")
            continue
        tokens, edges = build_graph_from_tickers(tickers)
        print(f"Tokens ({len(tokens)}):", tokens)
        print(f"Edges ({len(edges)}):")
        for e in edges[:20]:
            print(e)
        print(f"Total edges: {len(edges)}")
        # Simple connectivity check
        from collections import defaultdict, deque
        graph = defaultdict(list)
        for u, v, w in edges:
            graph[u].append(v)
        # BFS from first token
        if tokens:
            visited = set()
            q = deque([tokens[0]])
            while q:
                node = q.popleft()
                if node in visited:
                    continue
                visited.add(node)
                for nbr in graph[node]:
                    if nbr not in visited:
                        q.append(nbr)
            print(f"Connected tokens from {tokens[0]}: {len(visited)} / {len(tokens)}")
        # Print sample tickers
        print("Sample tickers:")
        for sym in list(tickers.keys())[:10]:
            print(sym, tickers[sym])

if __name__ == "__main__":
    main()
