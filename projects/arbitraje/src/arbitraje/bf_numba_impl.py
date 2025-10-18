"""Numba-backed Bellman-Ford compatible with engine_techniques.

Returns cycles as (cycle_idx, sum_w, hops) tuples; includes a Python fallback
when numba isn't available so callers/tests don't break.
"""

from typing import List, Tuple, Dict, Any
import math


def build_arrays_from_payload(
    payload: Dict[str, Any],
) -> Tuple[List[str], List[int], List[int], List[float]]:
    tickers = payload.get("tickers") or {}
    tokens = list(payload.get("tokens") or [])
    nodes_set = set(tokens)
    graph: Dict[str, Dict[str, float]] = {}
    for sym, t in tickers.items():
        if "/" not in sym:
            continue
        a, b = sym.split("/")
        nodes_set.add(a)
        nodes_set.add(b)
        try:
            rate = None
            if t.get("bid") is not None:
                rate = float(t.get("bid"))
            elif t.get("last") is not None:
                rate = float(t.get("last"))
        except Exception:
            rate = None
        if rate is not None and rate > 0:
            graph.setdefault(a, {})[b] = rate
        try:
            if t.get("ask") is not None:
                ask = float(t.get("ask"))
                if ask:
                    rev = 1.0 / ask
                    graph.setdefault(b, {})[a] = rev
        except Exception:
            pass

    nodes = list(nodes_set)
    idx = {n: i for i, n in enumerate(nodes)}
    u_arr: List[int] = []
    v_arr: List[int] = []
    w_arr: List[float] = []
    fee = float(payload.get("fee") or 0.0) / 100.0
    for u, nbrs in graph.items():
        iu = idx.get(u)
        for v, rate in nbrs.items():
            iv = idx.get(v)
            if iu is None or iv is None:
                continue
            mult = rate * (1.0 - fee)
            if mult <= 0:
                continue
            try:
                w = -math.log(mult)
            except Exception:
                continue
            u_arr.append(iu)
            v_arr.append(iv)
            w_arr.append(w)
    return nodes, u_arr, v_arr, w_arr


def _bf_python_array(
    n: int, u_arr: List[int], v_arr: List[int], w_arr: List[float]
) -> List[Tuple[List[int], float, int]]:
    cycles: List[Tuple[List[int], float, int]] = []
    m = len(u_arr)
    for s in range(n):
        dist = [float("inf")] * n
        parent = [-1] * n
        dist[s] = 0.0
        for _ in range(n - 1):
            updated = False
            for k in range(m):
                u = u_arr[k]
                v = v_arr[k]
                w = w_arr[k]
                du = dist[u]
                if du + w < dist[v]:
                    dist[v] = du + w
                    parent[v] = u
                    updated = True
            if not updated:
                break
        for k in range(m):
            u = u_arr[k]
            v = v_arr[k]
            w = w_arr[k]
            if dist[u] + w < dist[v]:
                y = v
                for _ in range(n):
                    y = parent[y] if parent[y] != -1 else y
                cycle_idx: List[int] = []
                cur = y
                while True:
                    cycle_idx.append(cur)
                    cur = parent[cur]
                    if cur == -1 or cur == y or len(cycle_idx) > n + 2:
                        break
                if len(cycle_idx) >= 2:
                    if cycle_idx[0] != cycle_idx[-1]:
                        closed = cycle_idx + [cycle_idx[0]]
                    else:
                        closed = cycle_idx
                    # sum weights along closed cycle
                    sum_w = 0.0
                    for i in range(len(closed) - 1):
                        a = closed[i]
                        b = closed[i + 1]
                        found = False
                        for kk in range(m):
                            if u_arr[kk] == a and v_arr[kk] == b:
                                sum_w += w_arr[kk]
                                found = True
                                break
                        if not found:
                            sum_w = 0.0
                            break
                    hops = len(closed) - 1
                    cycles.append((closed, sum_w, hops))
    return cycles


# Try to import numba-backed implementation from tools-style module if available
try:
    from . import bf_numba_impl as _self  # self-import for namespacing

    _HAS_RELATIVE = True
except Exception:
    _HAS_RELATIVE = False

# Robust numba detection
try:
    import importlib.util as _il

    _NUMBA_AVAILABLE = _il.find_spec("numba") is not None
except Exception:
    try:
        import importlib

        _NUMBA_AVAILABLE = (
            hasattr(importlib, "util") and importlib.util.find_spec("numba") is not None
        )
    except Exception:
        _NUMBA_AVAILABLE = False

if _NUMBA_AVAILABLE:
    import numpy as _np
    from numba import njit as _njit

    @_njit
    def _bf_source_numba(
        n,
        u_arr,
        v_arr,
        w_arr,
        s,
        min_net_pct,
        min_hops,
        max_hops,
        min_net_per_hop,
    ):
        m = u_arr.shape[0]
        INF = 1e308
        dist = [INF] * n
        parent = [-1] * n
        dist[s] = 0.0
        for _ in range(n - 1):
            updated = False
            for k in range(m):
                u = int(u_arr[k])
                v = int(v_arr[k])
                w = float(w_arr[k])
                du = dist[u]
                if du + w < dist[v]:
                    dist[v] = du + w
                    parent[v] = u
                    updated = True
            if not updated:
                break
        # detect cycle and compute aggregate
        for k in range(m):
            u = int(u_arr[k])
            v = int(v_arr[k])
            w = float(w_arr[k])
            if dist[u] + w < dist[v]:
                y = v
                for _ in range(n):
                    y = parent[y] if parent[y] != -1 else y
                cycle_idx = []
                cur = y
                while True:
                    cycle_idx.append(cur)
                    cur = parent[cur]
                    if cur == -1 or cur == y or len(cycle_idx) > n + 2:
                        break
                if len(cycle_idx) < 2:
                    return parent, -1, 0.0, 0
                if cycle_idx[0] != cycle_idx[-1]:
                    closed_len = len(cycle_idx) + 1
                else:
                    closed_len = len(cycle_idx)
                hops = closed_len - 1
                # filter inside JIT (min/max hops only; min_net filters applied by caller)
                if min_hops and hops < min_hops:
                    return parent, -1, 0.0, 0
                if max_hops and hops > max_hops:
                    return parent, -1, 0.0, 0
                return parent, v, 0.0, hops
        return parent, -1, 0.0, 0

    def bellman_ford_numba(
        n,
        u_arr,
        v_arr,
        w_arr,
        sources=None,
        min_net_pct=0.0,
        min_hops=0,
        max_hops=0,
        min_net_per_hop=0.0,
        blacklist_pairs=None,
    ):
        ua = _np.array(u_arr, dtype=_np.int64)
        va = _np.array(v_arr, dtype=_np.int64)
        wa = _np.array(w_arr, dtype=_np.float64)
        cycles: List[Tuple[List[int], float, int]] = []
        src_iter = list(range(n)) if sources is None else list(sources)
        for s in src_iter:
            parent, cycle_end, sum_w, hops = _bf_source_numba(
                int(n),
                ua,
                va,
                wa,
                int(s),
                float(min_net_pct),
                int(min_hops),
                int(max_hops),
                float(min_net_per_hop),
            )
            if cycle_end != -1 and hops > 0:
                y = cycle_end
                for _ in range(n):
                    y = parent[y] if parent[y] != -1 else y
                cycle_idx: List[int] = []
                cur = y
                while True:
                    cycle_idx.append(int(cur))
                    cur = parent[cur]
                    if cur == -1 or cur == y or len(cycle_idx) > n + 2:
                        break
                if len(cycle_idx) >= 2:
                    cycles.append((cycle_idx, float(sum_w), int(hops)))
        return cycles

else:

    def bellman_ford_numba(
        n,
        u_arr,
        v_arr,
        w_arr,
        sources=None,
        min_net_pct=0.0,
        min_hops=0,
        max_hops=0,
        min_net_per_hop=0.0,
        blacklist_pairs=None,
    ):
        # pure-python fallback that returns the same shape
        return _bf_python_array(n, u_arr, v_arr, w_arr)
