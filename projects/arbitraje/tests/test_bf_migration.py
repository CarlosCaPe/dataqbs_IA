import time
import pickle

from arbitraje import arbitrage_report_ccxt as arc
from arbitraje.engine_techniques import scan_arbitrage


def make_synthetic_tickers():
    tickers = {}
    pairs = ["A/USDT", "B/USDT", "C/USDT", "A/B", "B/C", "C/A"]
    for p in pairs:
        tickers[p] = {"bid": 1.0, "ask": 1.0, "last": 1.0, "quoteVolume": 1000}
    # make a profitable cycle
    tickers["A/B"]["bid"] = 1.02
    tickers["B/C"]["bid"] = 1.02
    tickers["C/A"]["bid"] = 1.02
    return tickers


def local_bf_snapshot_search(tickers, fee_pct=0.10, min_net=0.0):
    # replicate core of build_rates + bf detection but in-process on provided tickers
    tokens = ["A", "B", "C", "USDT"]
    currencies = [t for t in tokens]
    # candidate pairs where market exists
    candidate_pairs = [(u, v) for u in currencies for v in currencies if u != v]
    edges, rate_map = arc.build_rates_for_exchange_from_pairs(
        currencies, tickers, fee_pct, candidate_pairs, require_topofbook=False
    )
    # run same BF algorithm (log-space)
    import math

    n = len(currencies)
    if n < 3 or not edges:
        return []
    dist = [0.0] * n
    pred = [-1] * n
    for _ in range(n - 1):
        updated = False
        for u, v, w in edges:
            if dist[u] + w < dist[v] - 1e-12:
                dist[v] = dist[u] + w
                pred[v] = u
                updated = True
        if not updated:
            break
    results = []
    idx_map = {c: i for i, c in enumerate(currencies)}
    for u, v, w in edges:
        if dist[u] + w < dist[v] - 1e-12:
            y = v
            for _ in range(n):
                y = pred[y] if pred[y] != -1 else y
            cycle_nodes_idx = []
            cur = y
            while True:
                cycle_nodes_idx.append(cur)
                cur = pred[cur]
                if cur == -1 or cur == y or len(cycle_nodes_idx) > n + 2:
                    break
            cycle_nodes = [currencies[i] for i in cycle_nodes_idx]
            if len(cycle_nodes) < 2:
                continue
            prod = 1.0
            valid = True
            for i in range(len(cycle_nodes) - 1):
                a = cycle_nodes[i]
                b = cycle_nodes[i + 1]
                u_i = idx_map.get(a, None)
                v_i = idx_map.get(b, None)
                if u_i is None or v_i is None:
                    valid = False
                    break
                rate = rate_map.get((u_i, v_i))
                if rate is None or rate <= 0:
                    valid = False
                    break
                prod *= rate
            if valid and cycle_nodes[0] != cycle_nodes[-1]:
                a = cycle_nodes[-1]
                b = cycle_nodes[0]
                u_i = idx_map.get(a, None)
                v_i = idx_map.get(b, None)
                if u_i is None or v_i is None:
                    valid = False
                else:
                    rate = rate_map.get((u_i, v_i))
                    if rate is None or rate <= 0:
                        valid = False
                    else:
                        prod *= rate
                        cycle_nodes.append(cycle_nodes[0])
            if not valid:
                continue
            net_pct = (prod - 1.0) * 100.0
            if net_pct >= min_net:
                results.append({"cycle": "->".join(cycle_nodes), "net_pct": net_pct})
    return results


def test_bf_equivalence_and_pickling():
    tickers = make_synthetic_tickers()
    payload = {
        "ex_id": "testex",
        "quote": "USDT",
        "tokens": ["A", "B", "C"],
        "tickers": tickers,
        "fee": 0.10,
        "min_quote_vol": 0.0,
        "min_net": 0.0,
        "ts": "tst",
    }
    cfg = {"techniques": {"enabled": ["bellman_ford"], "max_workers": 1}}

    # run local in-process bf
    local = local_bf_snapshot_search(tickers, fee_pct=0.10, min_net=0.0)

    # run process-pool technique via scan_arbitrage
    res = scan_arbitrage("snap1", payload, cfg)

    assert isinstance(res, list)
    assert len(res) >= 1

    # pickling size/time
    t0p = time.time()
    p = pickle.dumps(payload)
    t1p = time.time()
    size = len(p)
    assert size < 200_000
    assert (t1p - t0p) < 1.0

    # at least one overlapping cycle string
    local_cycles = {r["cycle"] for r in local}
    res_cycles = {r.get("cycle") for r in res}
    assert local_cycles & res_cycles
