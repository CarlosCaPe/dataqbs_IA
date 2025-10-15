from __future__ import annotations

import logging
import os
import time
import json
from concurrent.futures import ThreadPoolExecutor, TimeoutError as ThreadTimeoutError
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import Callable, Dict, List

logger = logging.getLogger("arbitraje.engine_techniques")

# Types are expected to match project types; use light aliases to avoid heavy imports
Edge = object


class ArbResult(dict):
    """Minimal ArbResult container (dict-like) to remain compatible with callers."""


# --- Technique stubs (users will later map these to real implementations) ---
def _tech_bellman_ford(
    snapshot_id: str, edges: List[Edge], cfg: Dict
) -> List[ArbResult]:
    logger.debug("_tech_bellman_ford running snapshot=%s", snapshot_id)
    try:
        # Expect a payload dict with tickers and tokens to avoid any network IO here.
        if not isinstance(edges, dict):
            logger.debug("_tech_bellman_ford received non-payload edges; skipping")
            return []

        payload = edges
        tickers = payload.get("tickers") or {}
        fee = float(payload.get("fee") or 0.0)
        min_net = float(payload.get("min_net") or 0.0)
        ts_now = payload.get("ts") or snapshot_id
        ex_id = payload.get("ex_id")
        tokens = list(payload.get("tokens") or [])
        top_n = int(payload.get("top") or 20)
        min_hops = int(payload.get("min_hops") or 0)
        max_hops = int(payload.get("max_hops") or 0)
        min_net_per_hop = float(payload.get("min_net_per_hop") or 0.0)
        latency_penalty = float(payload.get("latency_penalty") or 0.0)
        blacklist = set(payload.get("blacklist") or [])

        # Build quick adjacency/graph from the supplied tickers
        graph: Dict[str, Dict[str, float]] = {}
        nodes_set = set(tokens)
        for sym, t in tickers.items():
            if "/" not in sym:
                continue
            a, b = sym.split("/")
            # prefer bid for selling a->b, else last
            rate = None
            try:
                if t.get("bid") is not None:
                    rate = float(t.get("bid"))
                elif t.get("last") is not None:
                    rate = float(t.get("last"))
            except Exception:
                rate = None
            if rate is not None and rate > 0:
                graph.setdefault(a, {})[b] = rate
                nodes_set.add(a)
                nodes_set.add(b)
            # consider reverse via ask
            try:
                if t.get("ask") is not None:
                    ask = float(t.get("ask"))
                    if ask:
                        rev = 1.0 / ask
                        graph.setdefault(b, {})[a] = rev
            except Exception:
                pass

        # Minimal node set
        nodes = list(nodes_set)
        if len(nodes) < 3:
            return []

        import math

        fee_frac = float(fee) / 100.0 if fee else 0.0

        # Build edge list in index form for Bellman-Ford in log space
        idx = {n: i for i, n in enumerate(nodes)}
        n = len(nodes)
        edge_list = []
        rate_map: Dict[tuple, float] = {}
        for u, nbrs in graph.items():
            for v, rate in nbrs.items():
                if u not in idx or v not in idx:
                    continue
                mult = rate * (1.0 - fee_frac)
                if mult <= 0:
                    continue
                try:
                    w = -math.log(mult)
                except Exception:
                    continue
                edge_list.append((idx[u], idx[v], w, u, v))
                rate_map[(idx[u], idx[v])] = mult

        results: List[ArbResult] = []
        seen_cycles: set = set()

        # Run Bellman-Ford from each source to detect negative cycles
        for s in range(n):
            dist = [float("inf")] * n
            parent = [-1] * n
            dist[s] = 0.0
            for _ in range(n - 1):
                updated = False
                for u, v, w, uu, vv in edge_list:
                    if dist[u] + w < dist[v]:
                        dist[v] = dist[u] + w
                        parent[v] = u
                        updated = True
                if not updated:
                    break
            # check for cycle
            for u, v, w, uu, vv in edge_list:
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
                    cycle_nodes = [nodes[i] for i in cycle_idx]
                    if len(cycle_nodes) < 2:
                        continue
                    # normalize and rotate to include an anchor if present (not enforced here)
                    key = tuple(cycle_nodes)
                    if key in seen_cycles:
                        continue
                    seen_cycles.add(key)

                    # compute product along cycle using rate_map where available
                    prod = 1.0
                    valid = True
                    for i in range(len(cycle_nodes) - 1):
                        a = cycle_nodes[i]
                        b = cycle_nodes[i + 1]
                        u_i = idx.get(a)
                        v_i = idx.get(b)
                        if u_i is None or v_i is None:
                            valid = False
                            break
                        rate = rate_map.get((u_i, v_i))
                        if rate is None or rate <= 0:
                            valid = False
                            break
                        prod *= rate
                    # close cycle
                    if valid and cycle_nodes[0] != cycle_nodes[-1]:
                        a = cycle_nodes[-1]
                        b = cycle_nodes[0]
                        u_i = idx.get(a)
                        v_i = idx.get(b)
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

                    hops = len(cycle_nodes) - 1
                    # hops filters
                    if (min_hops and hops < min_hops) or (max_hops and hops > max_hops):
                        continue

                    net_pct = (prod - 1.0) * 100.0
                    if net_pct < min_net:
                        continue
                    if min_net_per_hop and (net_pct / max(1, hops)) < min_net_per_hop:
                        continue

                    # blacklist check on pair-level
                    path_pairs = []
                    for i in range(len(cycle_nodes) - 1):
                        path_pairs.append(f"{cycle_nodes[i]}->{cycle_nodes[i+1]}")
                    if any(p in blacklist for p in path_pairs):
                        continue

                    net_bps = (prod - 1.0) * 10000.0
                    rec = {
                        "ts": ts_now,
                        "venue": ex_id,
                        "cycle": "->".join(cycle_nodes),
                        "net_bps_est": round(net_bps - latency_penalty, 4),
                        "fee_bps_total": round(hops * fee * 1.0, 6),
                        "status": "actionable",
                    }
                    results.append(rec)
                    if len(results) >= top_n:
                        return results

        return results
    except Exception:
        logger.exception("_tech_bellman_ford failed")
        return []


def _tech_bfs_depth(snapshot_id: str, edges: List[Edge], cfg: Dict) -> List[ArbResult]:
    logger.debug(
        "_tech_bfs_depth running snapshot=%s edges=%d", snapshot_id, len(edges)
    )
    return []


def _tech_stat_triangles(
    snapshot_id: str, edges: List[Edge], cfg: Dict
) -> List[ArbResult]:
    logger.debug("_tech_stat_triangles running snapshot=%s", snapshot_id)
    try:
        # If edges is a dict payload (preferred), unpack it
        if isinstance(edges, dict):
            payload = edges
            ex_id = payload.get("ex_id")
            quote = payload.get("quote")
            tokens = payload.get("tokens") or []
            tickers = payload.get("tickers") or {}
            fee = float(payload.get("fee") or 0.0)
            min_quote_vol = float(payload.get("min_quote_vol") or 0.0)
            min_net = float(payload.get("min_net") or 0.0)
            latency_penalty = float(payload.get("latency_penalty") or 0.0)
            ts_now = payload.get("ts") or snapshot_id

            results: List[ArbResult] = []
            fee_bps_total = 3.0 * fee

            def get_rate_and_qvol_local(a: str, b: str):
                sym = f"{a}/{b}"
                t = tickers.get(sym) or {}
                try:
                    bid = t.get("bid")
                    ask = t.get("ask")
                    if bid is None or ask is None:
                        last = t.get("last")
                        if last is not None:
                            return float(last), None
                        return None, None
                    rate = (float(bid) + float(ask)) / 2.0
                    qvol = float(t.get("quoteVolume") or t.get("quoteVolume24h") or 0.0)
                    return rate, qvol
                except Exception:
                    return None, None

            from itertools import permutations

            # Precompute maps
            r1_map = {}
            r3_map = {}
            for tkn in tokens:
                r1_map[tkn] = get_rate_and_qvol_local(quote, tkn)
                r3_map[tkn] = get_rate_and_qvol_local(tkn, quote)

            for X, Y in permutations(tokens, 2):
                r1, qv1 = r1_map.get(X, (None, None))
                if not r1:
                    continue
                if min_quote_vol > 0 and (qv1 is None or qv1 < min_quote_vol):
                    continue

                r2, qv2 = get_rate_and_qvol_local(X, Y)
                if not r2:
                    continue
                if min_quote_vol > 0 and (qv2 is None or qv2 < min_quote_vol):
                    continue

                r3, qv3 = r3_map.get(Y, (None, None))
                if not r3:
                    continue
                if min_quote_vol > 0 and (qv3 is None or qv3 < min_quote_vol):
                    continue

                gross_bps = (r1 * r2 * r3 - 1.0) * 10000.0
                net_bps = gross_bps - fee_bps_total
                if net_bps >= min_net:
                    rec = {
                        "ts": ts_now,
                        "venue": ex_id,
                        "cycle": f"{quote}->{X}->{Y}->{quote}",
                        "net_bps_est": round(net_bps - latency_penalty, 4),
                        "fee_bps_total": fee_bps_total,
                        "status": "actionable",
                    }
                    results.append(rec)
            return results
        else:
            logger.debug("_tech_stat_triangles received non-payload edges; skipping")
            return []
    except Exception:
        logger.exception("_tech_stat_triangles failed")
        return []


def _tech_ilp_cvxpy(snapshot_id: str, edges: List[Edge], cfg: Dict) -> List[ArbResult]:
    logger.debug(
        "_tech_ilp_cvxpy running snapshot=%s edges=%d", snapshot_id, len(edges)
    )
    return []


def _tech_dp_numba(snapshot_id: str, edges: List[Edge], cfg: Dict) -> List[ArbResult]:
    logger.debug("_tech_dp_numba running snapshot=%s edges=%d", snapshot_id, len(edges))
    return []


def _tech_rerank_onnx(
    snapshot_id: str, edges: List[Edge], cfg: Dict, base: List[ArbResult]
) -> List[ArbResult]:
    logger.debug(
        "_tech_rerank_onnx running snapshot=%s base=%d", snapshot_id, len(base)
    )
    return base


# Registry of available techniques
_TECHS: Dict[str, Callable] = {
    "bellman_ford": _tech_bellman_ford,
    "bfs_depth": _tech_bfs_depth,
    "stat_tri": _tech_stat_triangles,
    "ilp": _tech_ilp_cvxpy,
    "dp": _tech_dp_numba,
}


# Singleton process pool to avoid spawn overhead across iterations
_POOL: ProcessPoolExecutor | None = None


def _get_pool(max_workers: int) -> ProcessPoolExecutor:
    global _POOL
    if _POOL is None:
        _POOL = ProcessPoolExecutor(max_workers=max_workers)
    return _POOL


def _merge_results(results: List[ArbResult], cfg: Dict) -> List[ArbResult]:
    # Placeholder: keep minimal behavior — return results as-is.
    return results


def scan_arbitrage(snapshot_id: str, edges: List[Edge], cfg: Dict) -> List[ArbResult]:
    """Run enabled techniques in parallel and merge results.

    This function keeps IO out of the worker processes and only returns pure
    ArbResult objects for the caller to persist.
    """
    enabled = cfg.get("techniques", {}).get("enabled", list(_TECHS.keys()))
    if not enabled:
        return []

    maxw = cfg.get("techniques", {}).get(
        "max_workers", min(len(enabled), (os.cpu_count() or 4))
    )
    pool = _get_pool(maxw)

    futures = []
    results: List[ArbResult] = []
    # telemetry/stats per technique
    stats: Dict[str, Dict[str, float]] = {}
    future_map: Dict = {}
    # overall telemetry counters
    telemetry_counters = {
        "total_runs": 0,
        "fallback_count": 0,
        "fallback_timeouts": 0,
    }
    try:
        for name in enabled:
            func = _TECHS.get(name)
            if not func:
                logger.warning("Technique %s not found; skipping", name)
                continue
            fut = pool.submit(func, snapshot_id, edges, cfg)
            futures.append(fut)
            # record submit time to approximate worker duration
            future_map[fut] = (name, time.time())
            # init stats
            stats.setdefault(name, {"count": 0.0, "total_time": 0.0})

        for f in as_completed(futures):
            name, submit_ts = future_map.get(f, ("unknown", time.time()))
            start_wait = submit_ts
            end_wait = time.time()
            duration = max(0.0, end_wait - start_wait)
            try:
                res = f.result()
                # update stats
                stats.setdefault(name, {"count": 0.0, "total_time": 0.0})
                stats[name]["count"] += len(res) if res else 0.0
                stats[name]["total_time"] += duration
                if res:
                    results.extend(res)
            except Exception:
                logger.exception("Technique task %s failed; attempting fallback if available", name)
                # safe fallback for bellman_ford: run in a thread with timeout to avoid blocking
                if name == "bellman_ford":
                    fb_timeout = float(cfg.get("techniques", {}).get("fallback_timeout", 5.0))
                    try:
                        with ThreadPoolExecutor(max_workers=1) as thpool:
                            fb_future = thpool.submit(_tech_bellman_ford, snapshot_id, edges, cfg)
                            fb_res = fb_future.result(timeout=fb_timeout)
                            fb_dur = time.time() - submit_ts if submit_ts else 0.0
                            logger.warning("bellman_ford fallback produced %d results (timeout %.2fs)", len(fb_res) if fb_res else 0, fb_timeout)
                            stats.setdefault(name, {"count": 0.0, "total_time": 0.0})
                            stats[name]["count"] += len(fb_res) if fb_res else 0.0
                            stats[name]["total_time"] += fb_dur
                            if fb_res:
                                results.extend(fb_res)
                            telemetry_counters["fallback_count"] += 1
                    except ThreadTimeoutError:
                        logger.warning("bellman_ford fallback timed out after %.2fs", fb_timeout)
                        telemetry_counters["fallback_timeouts"] += 1
                    except Exception:
                        logger.exception("bellman_ford fallback also failed")
                else:
                    logger.warning("No fallback implemented for technique %s", name)

        # Optional rerank post-process
        if cfg.get("techniques", {}).get("enable_rerank_onnx", False):
            results = _tech_rerank_onnx(snapshot_id, edges, cfg, results)

        # emit a brief telemetry summary (counts and approximate time)
        try:
            size_bytes = 0
            try:
                size_bytes = len(json.dumps(edges))
            except Exception:
                size_bytes = 0
            logger.info("scan_arbitrage summary: techniques=%s results=%d payload_bytes=%d", list(stats.keys()), len(results), size_bytes)
            for nm, s in stats.items():
                logger.info("tech=%s result_count=%s total_time=%.3fs", nm, int(s.get("count") or 0), float(s.get("total_time") or 0.0))
            # add overall telemetry
            telemetry_counters["total_runs"] += 1
            summary = {
                "snapshot_id": snapshot_id,
                "timestamp": int(time.time()),
                "payload_bytes": size_bytes,
                "techniques": list(stats.keys()),
                "results_count": len(results),
                "telemetry": telemetry_counters,
            }
            logger.info("scan_arbitrage telemetry: %s", summary)
            # optional persistent telemetry file (append json line)
            try:
                telemetry_file = cfg.get("techniques", {}).get("telemetry_file")
                if telemetry_file:
                    with open(telemetry_file, "a", encoding="utf-8") as fh:
                        fh.write(json.dumps(summary) + "\n")
            except Exception:
                logger.debug("failed to write telemetry file")
        except Exception:
            logger.debug("failed to emit scan_arbitrage telemetry")

        return _merge_results(results, cfg)
    except Exception:
        logger.exception("scan_arbitrage failed; returning empty result")
        return []
