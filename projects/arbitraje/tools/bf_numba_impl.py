"""Prototype numeric Bellman-Ford using arrays with optional Numba JIT.

This is a self-contained prototype for experimentation. It does not replace
`_tech_bellman_ford` yet; that should be done after validating correctness
and performance.
"""

from typing import List, Tuple, Dict, Any
import math

# detect numba availability robustly (some minimal Python embed may lack importlib.util)
try:
    import importlib.util as _il

    _numba_available = _il.find_spec("numba") is not None
except Exception:
    try:
        import importlib

        _numba_available = (
            hasattr(importlib, "util") and importlib.util.find_spec("numba") is not None
        )
    except Exception:
        _numba_available = False

if _numba_available:
    from numba import njit
else:
    njit = None  # type: ignore


def build_arrays_from_payload(
    payload: Dict[str, Any],
) -> Tuple[List[str], List[int], List[int], List[float]]:
    tickers = payload.get("tickers") or {}
    tokens = list(payload.get("tokens") or [])
    nodes_set = set(tokens)
    graph = {}
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
    u_arr = []
    v_arr = []
    w_arr = []
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


def bellman_ford_array(
    n: int, u_arr: List[int], v_arr: List[int], w_arr: List[float]
) -> List[List[int]]:
    """Naive BF over arrays: detect any negative cycle and return cycles as index-lists.
    Returns a list of cycles (each cycle is a list of node indices).
    """
    cycles = []
    m = len(u_arr)
    for s in range(n):
        dist = [float("inf")] * n
        parent = [-1] * n
        dist[s] = 0.0
        # relax edges
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
        # check for negative cycles
        for k in range(m):
            u = u_arr[k]
            v = v_arr[k]
            w = w_arr[k]
            if dist[u] + w < dist[v]:
                # reconstruct cycle
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
                if len(cycle_idx) >= 2:
                    cycles.append(cycle_idx)
    return cycles


# Optional Numba JIT wrapper
if _numba_available:
    # Create numba-supported versions by translating lists to typed lists/arrays
    import numpy as _np
    from numba import njit

    @njit
    def _bf_source_numba(n, u_arr, v_arr, w_arr, s, min_net_pct, min_hops, max_hops, min_net_per_hop, bl_u, bl_v, bl_len):
        # Bellman-Ford for a single source s.
        # Returns parent array, cycle_end index or -1, sum_w along cycle, and hops.
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
        # detect a negative cycle
        for k in range(m):
            u = int(u_arr[k])
            v = int(v_arr[k])
            w = float(w_arr[k])
            if dist[u] + w < dist[v]:
                # reconstruct cycle
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
                # ensure closed cycle
                if cycle_idx[0] != cycle_idx[-1]:
                    closed = cycle_idx + [cycle_idx[0]]
                else:
                    closed = cycle_idx
                # compute sum of w along closed cycle by scanning edges
                sum_w = 0.0
                for i in range(len(closed) - 1):
                    a = closed[i]
                    b = closed[i + 1]
                    # find matching edge
                    found = False
                    for kk in range(m):
                        if int(u_arr[kk]) == a and int(v_arr[kk]) == b:
                            sum_w += float(w_arr[kk])
                            found = True
                            break
                    if not found:
                        # missing edge weight, mark as invalid
                        return parent, -1, 0.0, 0
                hops = len(closed) - 1
                # compute product via exp(-sum_w)
                prod = _np.exp(-sum_w)
                net_pct = (prod - 1.0) * 100.0
                # apply filters inside JIT
                if min_hops and hops < min_hops:
                    return parent, -1, 0.0, 0
                if max_hops and hops > max_hops:
                    return parent, -1, 0.0, 0
                if net_pct < min_net_pct:
                    return parent, -1, 0.0, 0
                if min_net_per_hop and (net_pct / max(1, hops)) < min_net_per_hop:
                    return parent, -1, 0.0, 0
                # blacklist check: bl_u/bl_v arrays of length bl_len
                if bl_len and bl_u is not None and bl_v is not None:
                    for i in range(len(closed) - 1):
                        a = closed[i]
                        b = closed[i + 1]
                        for bi in range(bl_len):
                            if bl_u[bi] == a and bl_v[bi] == b:
                                return parent, -1, 0.0, 0
                return parent, v, sum_w, hops
        return parent, -1, 0.0, 0

    def warmup_numba():
        """Run a tiny dummy call to trigger Numba compilation for the jitted function.

        This should be called once at process startup to amortize JIT latency.
        """
        import numpy as _np

        # tiny dummy graph: 3 nodes, a single edge
        ua = _np.array([0], dtype=_np.int64)
        va = _np.array([1], dtype=_np.int64)
        wa = _np.array([0.1], dtype=_np.float64)
        # call a single source to JIT compile
        try:
            bl_u = _np.empty(0, dtype=_np.int64)
            bl_v = _np.empty(0, dtype=_np.int64)
            _bf_source_numba(3, ua, va, wa, 0, 0.0, 0, 0, 0.0, bl_u, bl_v, 0)
        except Exception:
            # ignore compilation/runtime exceptions during warmup
            pass

    def bellman_ford_numba(n, u_arr, v_arr, w_arr, sources=None, min_net_pct=0.0, min_hops=0, max_hops=0, min_net_per_hop=0.0, blacklist_pairs=None):
        # wrapper: call per-source jitted function and reconstruct cycles in Python
        import numpy as np

        ua = np.array(u_arr, dtype=np.int64)
        va = np.array(v_arr, dtype=np.int64)
        wa = np.array(w_arr, dtype=np.float64)
        cycles = []
        # if sources is provided, iterate only those; otherwise iterate all
        if sources is None:
            source_iter = range(n)
        else:
            source_iter = list(sources)
        # prepare blacklist arrays for numba if provided
        if blacklist_pairs:
            bl_u = np.array([p[0] for p in blacklist_pairs], dtype=np.int64)
            bl_v = np.array([p[1] for p in blacklist_pairs], dtype=np.int64)
            bl_len = bl_u.shape[0]
        else:
            bl_u = np.empty(0, dtype=np.int64)
            bl_v = np.empty(0, dtype=np.int64)
            bl_len = 0
        for s in source_iter:
            # parent, cycle_end, sum_w, hops
            res = _bf_source_numba(n, ua, va, wa, int(s), float(min_net_pct), int(min_hops), int(max_hops), float(min_net_per_hop), bl_u, bl_v, bl_len)
            parent = res[0]
            cycle_end = res[1]
            sum_w = res[2]
            hops = int(res[3])
            if cycle_end != -1 and hops > 0:
                # reconstruct cycle indices from parent
                y = cycle_end
                for _ in range(n):
                    y = parent[y] if parent[y] != -1 else y
                cycle_idx = []
                cur = y
                while True:
                    cycle_idx.append(int(cur))
                    cur = parent[cur]
                    if cur == -1 or cur == y or len(cycle_idx) > n + 2:
                        break
                if len(cycle_idx) >= 2:
                    cycles.append((cycle_idx, sum_w, hops))
        return cycles

else:
    bellman_ford_numba = None


if __name__ == "__main__":
    # quick smoke test
    import json
    from pathlib import Path

    p = (
        Path(__file__).resolve().parents[1]
        / "artifacts"
        / "arbitraje"
        / "offline_snapshot_synth_large.json"
    )
    with open(p, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    first = next(iter(data.keys()))
    payload = data[first]
    nodes, u_arr, v_arr, w_arr = build_arrays_from_payload(payload)
    print("nodes", len(nodes), "edges", len(u_arr))
    cycles = bellman_ford_array(len(nodes), u_arr, v_arr, w_arr)
    print("found cycles (count):", len(cycles))
