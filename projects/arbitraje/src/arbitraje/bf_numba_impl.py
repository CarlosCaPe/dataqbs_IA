"""Prototype numeric Bellman-Ford using arrays with optional Numba JIT.

This is una versión mínima para soporte de tests y engine.
"""

try:
    import numba
except ImportError:
    numba = None

def build_arrays_from_payload(payload):
    # Extrae nodos y edges de un payload de snapshot sintético
    tokens = payload.get("tokens") or []
    tickers = payload.get("tickers") or {}
    fee = float(payload.get("fee") or 0.0)
    idx_map = {c: i for i, c in enumerate(tokens)}
    u_arr, v_arr, w_arr = [], [], []
    for sym, t in tickers.items():
        if not isinstance(t, dict):
            continue
        parts = sym.split("/")
        if len(parts) != 2:
            continue
        base, quote = parts
        if base in idx_map and quote in idx_map:
            u, v = idx_map[base], idx_map[quote]
            bid = t.get("bid")
            ask = t.get("ask")
            if bid and bid > 0:
                u_arr.append(u)
                v_arr.append(v)
                w_arr.append(-math.log(bid * (1 - fee / 100)))
            if ask and ask > 0:
                u_arr.append(v)
                v_arr.append(u)
                w_arr.append(-math.log(1 / ask * (1 - fee / 100)))
    return tokens, u_arr, v_arr, w_arr

if numba:
    import math
    @numba.njit
    def bellman_ford_numba(n, u_arr, v_arr, w_arr):
        dist = [0.0] * n
        pred = [-1] * n
        for _ in range(n - 1):
            for i in range(len(u_arr)):
                u, v, w = u_arr[i], v_arr[i], w_arr[i]
                if dist[u] + w < dist[v] - 1e-12:
                    dist[v] = dist[u] + w
                    pred[v] = u
        # Busca ciclos negativos
        for i in range(len(u_arr)):
            u, v, w = u_arr[i], v_arr[i], w_arr[i]
            if dist[u] + w < dist[v] - 1e-12:
                return True  # Hay ciclo
        return False
else:
    bellman_ford_numba = None
    build_arrays_from_payload = build_arrays_from_payload
    # fallback: no aceleración
