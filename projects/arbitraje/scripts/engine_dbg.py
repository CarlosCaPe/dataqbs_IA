import json, pathlib, importlib.util, math, sys
from pprint import pprint
from arbitraje import engine_techniques

# load bf_numba_impl module
bf_path = pathlib.Path(__file__).resolve().parents[1] / "tools" / "bf_numba_impl.py"
spec = importlib.util.spec_from_file_location("bf_numba_impl", str(bf_path))
bf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bf)

p = (
    pathlib.Path(__file__).resolve().parents[1]
    / "artifacts"
    / "arbitraje"
    / "offline_snapshot_profitable.json"
)
data = json.load(open(p, "r", encoding="utf-8"))
for ex, payload in data.items():
    print("\n=== EXCHANGE", ex)
    # emulate engine local extraction
    payload2 = dict(payload)
    payload2.update(
        {
            "fee": 0.10,
            "min_net": 0.0,
            "min_hops": 0,
            "max_hops": 0,
            "top": 200,
            "latency_penalty": 0.0,
        }
    )
    tickers = payload2.get("tickers") or {}
    tokens = list(payload2.get("tokens") or [])
    nodes_set = set(tokens)
    for sym, t in tickers.items():
        if "/" not in sym:
            continue
        a, b = sym.split("/")
        try:
            if t.get("bid") is not None:
                rate = float(t.get("bid"))
            elif t.get("last") is not None:
                rate = float(t.get("last"))
            else:
                rate = None
        except:
            rate = None
        if rate is not None and rate > 0:
            nodes_set.add(a)
            nodes_set.add(b)
        try:
            if t.get("ask") is not None:
                ask = float(t.get("ask"))
                if ask:
                    nodes_set.add(a)
                    nodes_set.add(b)
        except:
            pass
    nodes = list(nodes_set)
    print("nodes", nodes)
    idx = {n: i for i, n in enumerate(nodes)}
    fee_frac = float(payload2.get("fee") or 0.0) / 100.0 if payload2.get("fee") else 0.0
    edge_list = []
    rate_map = {}
    import math

    for sym, t in tickers.items():
        if "/" not in sym:
            continue
        a, b = sym.split("/")
        iu = idx.get(a)
        iv = idx.get(b)
        # get rate similar to engine
        try:
            if t.get("bid") is not None:
                rate = float(t.get("bid"))
            elif t.get("last") is not None:
                rate = float(t.get("last"))
            else:
                rate = None
        except:
            rate = None
        if rate is not None and rate > 0 and iu is not None and iv is not None:
            mult = rate * (1.0 - fee_frac)
            if mult > 0:
                w = -math.log(mult)
                edge_list.append((iu, iv, w))
                rate_map[(iu, iv)] = mult
        try:
            if t.get("ask") is not None:
                ask = float(t.get("ask"))
                if ask and iu is not None and iv is not None:
                    rev = 1.0 / ask
                    mult = rev * (1.0 - fee_frac)
                    edge_list.append((iv, iu, -math.log(mult)))
                    rate_map[(iv, iu)] = mult
        except:
            pass
    print("edge_list len", len(edge_list))
    # use bf array builder to get arrays
    nodes_b, u_arr, v_arr, w_arr = bf.build_arrays_from_payload(payload2)
    print("nodes_b", nodes_b, "edges_b", len(u_arr))
    cycles_arr = bf.bellman_ford_array(len(nodes_b), u_arr, v_arr, w_arr)
    print("cycles_arr", cycles_arr)
    # compute products using engine's rate_map
    for cyc in cycles_arr:
        closed = cyc if cyc[0] == cyc[-1] else cyc + [cyc[0]]
        prod = 1.0
        valid = True
        for i in range(len(closed) - 1):
            u = closed[i]
            v = closed[i + 1]
            r = rate_map.get((u, v))
            print("edge", nodes[u], "->", nodes[v], "rate_map", r)
            if r is None:
                valid = False
                break
            prod *= r
        print("prod", prod, "net_pct", (prod - 1.0) * 100.0, "valid", valid)
    print("\nCall engine function:")
    res = engine_techniques._tech_bellman_ford(
        ex, payload2, {"techniques": {"use_numba": False}, "bf": {}}
    )
    print("engine res len", len(res))
    if res:
        pprint(res)
