from __future__ import annotations

import json
from pathlib import Path
import logging
import os
import time
from concurrent.futures import (
    FIRST_COMPLETED,
    ProcessPoolExecutor,
    ThreadPoolExecutor,
    wait,
)
from concurrent.futures import TimeoutError as ThreadTimeoutError
from typing import Callable, Dict, List

logger = logging.getLogger("arbitraje.engine_techniques")

# Types are expected to match project types; use light aliases to avoid heavy imports
Edge = object


class ArbResult(dict):
    """Minimal ArbResult container (dict-like) to remain compatible with callers."""


# --- Technique stubs (users will later map these to real implementations) ---
def _tech_bellman_ford(
    import datetime
    diag_log_path = None
    try:
        diag_log_path = str(Path(__file__).resolve().parents[1] / "artifacts" / "arbitraje" / "diagnostics.log")
    except Exception:
        diag_log_path = None

    def diag_log(msg):
        if diag_log_path:
            try:
                with open(diag_log_path, "a", encoding="utf-8") as dfh:
                    dfh.write(f"[{datetime.datetime.utcnow().isoformat()}] {msg}\n")
            except Exception:
                pass

    t0 = time.time()
    snapshot_id: str, edges: List[Edge], cfg: Dict
) -> List[ArbResult]:
    logger.debug("_tech_bellman_ford running snapshot=%s", snapshot_id)
    try:
        # If a precomputed volatility map is attached to the payload, use it.
        # This avoids recalculating stddevs inside the hot loop repeatedly.
        pre_vol = None
        try:
            pre_vol = payload.get("_precomputed_volatility")
        except Exception:
            pre_vol = None
        # Expect a payload dict with tickers and tokens to avoid any network IO here.
        # Be defensive: callers may pass None or partial payloads; treat those
        # gracefully and return an empty result rather than raising.
        if not edges:
            logger.debug("_tech_bellman_ford received empty edges; skipping")
            return []

        # Prefer dict payloads. If a mapping-like object was passed, try to
        # coerce to dict; otherwise skip.
        if not isinstance(edges, dict):
            try:
                payload = dict(edges)
            except Exception:
                logger.debug(
                    "_tech_bellman_ford received non-dict edges (%s); skipping",
                    type(edges),
                )
                return []
        else:
            payload = edges

        tickers = payload.get("tickers") or {}
        if tickers is None or not isinstance(tickers, dict):
            logger.debug(
                "_tech_bellman_ford tickers missing or invalid; treating as empty"
            )
            tickers = {}

        # Diagnostic: log number of tickers and valid rates
        n_tickers = len(tickers)
        n_valid_rates = 0
        for t in tickers.values():
            try:
                if (t.get("bid") and float(t.get("bid")) > 0) or (t.get("ask") and float(t.get("ask")) > 0) or (t.get("last") and float(t.get("last")) > 0):
                    n_valid_rates += 1
            except Exception:
                pass
        diag_log(f"Tickers: {n_tickers}, Valid rates: {n_valid_rates}")

        t1 = time.time()
        diag_log(f"Tickers fetch/preprocess time: {t1-t0:.3f}s")

        # Allow BF tuning from the provided global config (cfg['bf']) with
        # fallback to any values carried inside the payload. This ensures CLI/YAML
        # overrides are respected (previously the engine only read from payload).
        bf_cfg = cfg.get("bf") or {}

        def _pick(key, cast, default=None):
            # prefer bf_cfg, then payload, then default
            if key in bf_cfg:
                try:
                    return cast(bf_cfg.get(key))
                except Exception:
                    return default
            try:
                if key in payload:
                    return cast(payload.get(key))
            except Exception:
                pass
            return default

        fee = float(_pick("fee", float, payload.get("fee") or 0.0))
        # min_net is expressed in percent (e.g. 0.15 -> 0.15%)
        min_net = float(_pick("min_net", float, 0.0))
        ts_now = payload.get("ts") or snapshot_id
        ex_id = payload.get("ex_id")
        tokens = list(_pick("tokens", list, payload.get("tokens") or []))
        top_n = int(_pick("top", int, payload.get("top") or 20))
        min_hops = int(_pick("min_hops", int, payload.get("min_hops") or 0))
        max_hops = int(_pick("max_hops", int, payload.get("max_hops") or 0))
        min_net_per_hop = float(_pick("min_net_per_hop", float, 0.0))
        latency_penalty = float(_pick("latency_penalty", float, 0.0))
        blacklist = set(_pick("blacklist", list, payload.get("blacklist") or []))

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

        # Diagnostic: log graph size before pruning
        n_graph_nodes = len(graph)
        n_graph_edges = sum(len(nbrs) for nbrs in graph.values())
        diag_log(f"Graph before pruning: nodes={n_graph_nodes}, edges={n_graph_edges}")

        # Minimal node set
        nodes = list(nodes_set)
        if len(nodes) < 3:
            return []

        import math

        # Micro-optimizations: bind locals for hot loops
        _log = math.log
        fee_frac = float(fee) / 100.0 if fee else 0.0

        # Build edge list in index form for Bellman-Ford in log space
        idx = {n: i for i, n in enumerate(nodes)}
        n = len(nodes)
        edge_list = []
        rate_map: Dict[tuple, float] = {}
        # localize frequently used names
        _idx_get = idx.get
        _edge_list_append = edge_list.append
        _rate_map_set = rate_map.__setitem__
        for u, nbrs in graph.items():
            if not nbrs:
                continue
            iu = _idx_get(u)
            for v, rate in nbrs.items():
                iv = _idx_get(v)
                if iu is None or iv is None:
                    continue
                mult = rate * (1.0 - fee_frac)
                if mult <= 0:
                    continue
                try:
                    w = -_log(mult)
                except Exception:
                    continue
                # store only indices and weight to reduce allocation of strings
                _edge_list_append((iu, iv, w))
                _rate_map_set((iu, iv), mult)

        results: List[ArbResult] = []
        seen_cycles: set = set()
        # Candidate cycle logging setup
        candidate_log_path = None
        try:
            candidate_log_path = str(Path(__file__).resolve().parents[1] / "artifacts" / "arbitraje" / "candidate_cycles.log")
        except Exception:
            candidate_log_path = None

        # Attempt to use Numba-accelerated BF if available (faster numeric core)
        use_numba = bool(cfg.get("techniques", {}).get("use_numba", True))
        try:
            # bf_numba_impl provides: bellman_ford_numba, build_arrays_from_payload, warmup_numba(optional)
            from bf_numba_impl import (
                bellman_ford_numba,
                build_arrays_from_payload,
                warmup_numba,
            )
        except Exception:
            bellman_ford_numba = None
            build_arrays_from_payload = None
            warmup_numba = None

        # Prepare arrays for numeric BF
        u_arr = [u for (u, v, w) in edge_list]
        v_arr = [v for (u, v, w) in edge_list]
        w_arr = [w for (u, v, w) in edge_list]

    # Diagnostic: log edge list size before pruning
    diag_log(f"Edge list before pruning: nodes={n}, edges={len(edge_list)}")

        if bellman_ford_numba is not None and use_numba:
            try:
                # Optional warm-up (compile) to amortize JIT overhead at startup
                try:
                    if warmup_numba is not None and cfg.get("techniques", {}).get(
                        "warmup_numba", False
                    ):
                        warmup_numba()
                except Exception:
                    logger.debug("numba warmup failed or skipped")

                # pruning: select a subset of sources based on node degree if configured
                pruning_threshold = int(
                    cfg.get("techniques", {}).get("pruning_degree_threshold", 0)
                )
                sources = None
                if pruning_threshold and edge_list:
                    deg = [0] * n
                    for u_i, v_i, _w in edge_list:
                        deg[u_i] += 1
                        deg[v_i] += 1
                    sources = [i for i, d in enumerate(deg) if d > pruning_threshold]

                # Diagnostic: log after degree pruning
                if pruning_threshold:
                    diag_log(f"After degree pruning: sources={len(sources) if sources else 0}")

                # Improved pruning heuristic: combine quoteVolume with a simple volatility metric
                qvol_threshold_frac = float(
                    cfg.get("techniques", {}).get("pruning_qvol_frac", 0.0)
                )
                pruning_volatility_window = int(
                    cfg.get("techniques", {}).get("pruning_volatility_window", 5)
                )
                if qvol_threshold_frac and tokens:
                    # compute per-token quoteVolume and volatility from tickers/history
                    qvol_map = {}
                    vol_map = {}
                    # If precomputed vol map exists, use it preferentially
                    if pre_vol and isinstance(pre_vol, dict):
                        for tok, v in pre_vol.items():
                            try:
                                vol_map[tok] = float(v)
                            except Exception:
                                vol_map[tok] = 0.0

                    for sym, t in tickers.items():
                        if "/" not in sym:
                            continue
                        a, b = sym.split("/")
                        # quoteVolume: support several key names and safe-cast
                        qv = 0.0
                        try:
                            qv = float(
                                t.get("quoteVolume")
                                or t.get("quoteVolume24h")
                                or t.get("quote_volume")
                                or 0.0
                            )
                        except Exception:
                            qv = 0.0
                        qvol_map[a] = max(qvol_map.get(a, 0.0), qv)
                        qvol_map[b] = max(qvol_map.get(b, 0.0), qv)

                        # volatility: look for tiny 'history' list in ticker dict; compute stddev of mid prices
                        hist = t.get("history") or t.get("ticks") or []
                        mids = []
                        try:
                            for tick in hist[-pruning_volatility_window:]:
                                bid = tick.get("bid")
                                ask = tick.get("ask")
                                if bid is not None and ask is not None:
                                    mids.append((float(bid) + float(ask)) / 2.0)
                                else:
                                    mids.append(
                                        float(
                                            tick.get("price") or tick.get("px") or 0.0
                                        )
                                    )
                        except Exception:
                            mids = []
                        if len(mids) >= 2:
                            mean = sum(mids) / len(mids)
                            var = sum((x - mean) ** 2 for x in mids) / max(
                                1, (len(mids) - 1)
                            )
                            vol_map[a] = max(vol_map.get(a, 0.0), float(var**0.5))
                            vol_map[b] = max(vol_map.get(b, 0.0), float(var**0.5))
                        else:
                            vol_map[a] = max(vol_map.get(a, 0.0), 0.0)
                            vol_map[b] = max(vol_map.get(b, 0.0), 0.0)

                    if qvol_map:
                        # compute combined score and pick top-k tokens
                        total_qvol = sum(qvol_map.values()) or 1.0
                        score_map = {
                            tok: qvol_map.get(tok, 0.0) * (1.0 + vol_map.get(tok, 0.0))
                            for tok in qvol_map
                        }
                        k = max(1, int(len(nodes) * qvol_threshold_frac))
                        sorted_tokens = sorted(
                            nodes, key=lambda x: score_map.get(x, 0.0), reverse=True
                        )
                        q_sources = [
                            idx.get(tok)
                            for tok in sorted_tokens[:k]
                            if idx.get(tok) is not None
                        ]
                        if sources is None:
                            sources = q_sources
                        else:
                            sources = [s for s in sources if s in q_sources]

                        # Diagnostic: log after qvol pruning
                        diag_log(f"After qvol pruning: sources={len(sources) if sources else 0}, k={k}, qvol_threshold_frac={qvol_threshold_frac}")

                # Call numba wrapper; if it supports a sources arg, pass it (it may ignore extra args)
                # time the numba call separately from Python postprocessing
                numba_call_start = time.time()
                # Build blacklist index pairs to pass to numba
                bl_pairs = None
                if blacklist:
                    bl_pairs = []
                    try:
                        for p in blacklist:
                            if isinstance(p, str) and "->" in p:
                                a_s, b_s = p.split("->", 1)
                                a_i = idx.get(a_s)
                                b_i = idx.get(b_s)
                                if a_i is not None and b_i is not None:
                                    bl_pairs.append((a_i, b_i))
                    except Exception:
                        bl_pairs = None

                try:
                    cycles_idx = bellman_ford_numba(
                        n,
                        u_arr,
                        v_arr,
                        w_arr,
                        sources=sources,
                        min_net_pct=min_net,
                        min_hops=min_hops,
                        max_hops=max_hops,
                        min_net_per_hop=min_net_per_hop,
                        blacklist_pairs=bl_pairs,
                    )
                except TypeError:
                    # older bf_numba_impl may not accept keyword args
                    cycles_idx = bellman_ford_numba(n, u_arr, v_arr, w_arr)
                numba_call_elapsed = time.time() - numba_call_start
                # cycles_idx is a list of lists of node indices representing cycles
                # Map cycles back to tokens and apply same filters as before
                # Precompute blacklist index pairs once
                bl_idx = set()
                if blacklist:
                    try:
                        for p in blacklist:
                            if isinstance(p, str) and "->" in p:
                                a_s, b_s = p.split("->", 1)
                                a_i = idx.get(a_s)
                                b_i = idx.get(b_s)
                                if a_i is not None and b_i is not None:
                                    bl_idx.add((a_i, b_i))
                    except Exception:
                        bl_idx = set()

                postproc_start = time.time()
                for entry in cycles_idx:
                    # entry may be either a plain cycle_idx (legacy) or (cycle_idx, sum_w, hops)
                    if not entry:
                        continue
                    sum_w = None
                    hops = None
                    if (
                        isinstance(entry, (list, tuple))
                        and len(entry) >= 3
                        and isinstance(entry[1], (float, int))
                    ):
                        cycle_idx = entry[0]
                        sum_w = float(entry[1])
                        hops = int(entry[2])
                    else:
                        cycle_idx = entry

                    # normalize and ensure ints
                    cycle_idx = [int(x) for x in cycle_idx]
                    # ensure closed cycle
                    if cycle_idx[0] != cycle_idx[-1]:
                        closed_idx = cycle_idx + [cycle_idx[0]]
                    else:
                        closed_idx = cycle_idx
                    if len(closed_idx) < 2:
                        continue

                    # node names
                    cycle_nodes = [nodes[i] for i in closed_idx]
                    key = tuple(cycle_nodes)
                    if key in seen_cycles:
                        continue
                    seen_cycles.add(key)

                    # Attempt to compute product for both forward and reversed orientations
                    # and pick the best one. This guards against the numeric core
                    # returning a cycle in the opposite traversal direction.
                    try:
                        if sum_w is not None and sum_w > 0:
                            import math as _math

                            prod_sumw = _math.exp(-sum_w)
                        else:
                            prod_sumw = None
                    except Exception:
                        prod_sumw = None

                    def _prod_for_idx(idx_path):
                        p = 1.0
                        for ii in range(len(idx_path) - 1):
                            u_i = idx_path[ii]
                            v_i = idx_path[ii + 1]
                            rate = rate_map.get((u_i, v_i))
                            if rate is None or rate <= 0:
                                return None
                            p *= rate
                        return p

                    prod_fw = _prod_for_idx(closed_idx)
                    rev_idx = list(reversed(closed_idx))
                    prod_rev = _prod_for_idx(rev_idx)

                    # choose the best available product among sum_w (if provided), forward, and reverse
                    candidates = [
                        x for x in (prod_sumw, prod_fw, prod_rev) if x is not None
                    ]
                    if not candidates:
                        continue
                    prod = max(candidates)
                    # prefer the reversed orientation if it produced the best product
                    if prod == prod_rev and prod_rev is not None:
                        closed_idx = rev_idx
                        cycle_nodes = [nodes[i] for i in closed_idx]
                        if hops is None:
                            hops = len(closed_idx) - 1

                    # filters
                    if hops is None:
                        hops = len(closed_idx) - 1
                    if (min_hops and hops < min_hops) or (max_hops and hops > max_hops):
                        continue
                    net_pct = (prod - 1.0) * 100.0
                    if net_pct < min_net:
                        continue
                    if min_net_per_hop and (net_pct / max(1, hops)) < min_net_per_hop:
                        continue

                    # blacklist check
                    if bl_idx:
                        blocked = False
                        for i in range(len(closed_idx) - 1):
                            if (closed_idx[i], closed_idx[i + 1]) in bl_idx:
                                blocked = True
                                break
                        if blocked:
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
                postproc_elapsed = time.time() - postproc_start
                # attach last telemetry blob on the function for scan_arbitrage to consume
                try:
                    _tech_bellman_ford._last_telemetry = {
                        "numba_call_s": numba_call_elapsed,
                        "postprocess_s": postproc_elapsed,
                        "numba_warmup_s": None,
                    }
                except Exception:
                    pass
                # slow-iteration logging
                try:
                    slow_thresh = float(
                        cfg.get("techniques", {}).get("slow_iteration_threshold_s", 0.8)
                    )
                    total_iter_s = (numba_call_elapsed or 0.0) + (
                        postproc_elapsed or 0.0
                    )
                    if slow_thresh and total_iter_s >= slow_thresh:
                        try:
                            art_dir = (
                                Path(__file__).resolve().parents[1]
                                / "artifacts"
                                / "arbitraje"
                            )
                            art_dir.mkdir(parents=True, exist_ok=True)
                            slow_log = art_dir / "slow_iterations.log"
                            with open(slow_log, "a", encoding="utf-8") as sfh:
                                sfh.write(
                                    json.dumps(
                                        {
                                            "snapshot_id": snapshot_id,
                                            "technique": "bellman_ford_numba",
                                            "numba_call_s": numba_call_elapsed,
                                            "postproc_s": postproc_elapsed,
                                            "total_s": total_iter_s,
                                            "results": len(results),
                                            "timestamp": int(time.time()),
                                        }
                                    )
                                    + "\n"
                                )
                        except Exception:
                            logger.debug("failed to write slow iteration log")
                except Exception:
                    pass
                return results
            except Exception:
                logger.exception(
                    "Numba BF path failed; falling back to Python implementation"
                )

        # Diagnostic helper: if no results were found and a diagnostic flag is set,
        # run the simpler array-based BF (bellman_ford_array) from bf_numba_impl to
        # surface any cycles we might be filtering out later in postprocessing.
        try:
            diag_enabled = bool(cfg.get("bf", {}).get("diagnose_force_array_bf", False))
            if diag_enabled:
                try:
                    from bf_numba_impl import bellman_ford_array

                    nodes2, ua, va, wa = build_arrays_from_payload(payload)
                    arr_cycles = bellman_ford_array(len(nodes2), ua, va, wa)
                    if arr_cycles:
                        logger.warning(
                            "Diagnostic BF-array found %d cycles (sample): %s",
                            len(arr_cycles),
                            arr_cycles[:3],
                        )
                except Exception:
                    pass
        except Exception:
            pass

        # fallback: original pure-Python BF loop
        for s in range(n):
            dist = [float("inf")] * n
            parent = [-1] * n
            dist[s] = 0.0
            # standard Bellman-Ford relaxations with early-exit
            for _ in range(n - 1):
                updated = False
                for u, v, w in edge_list:
                    du = dist[u]
                    if du + w < dist[v]:
                        dist[v] = du + w
                        parent[v] = u
                        updated = True
                if not updated:
                    break
            # check for cycle
            for u, v, w in edge_list:
                if dist[u] + w < dist[v]:
                    # reconstruct cycle (indices only)
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
                        continue
                    # ensure closed cycle (append first if missing)
                    if cycle_idx[0] != cycle_idx[-1]:
                        closed_idx = cycle_idx + [cycle_idx[0]]
                    else:
                        closed_idx = cycle_idx

                    # build node-name list once and use as canonical key
                    cycle_nodes = [nodes[i] for i in closed_idx]
                    key = tuple(cycle_nodes)
                    if key in seen_cycles:
                        continue
                    seen_cycles.add(key)

                    # compute product for both orientations
                    def _prod_for_idx_fb(idx_path):
                        p = 1.0
                        for ii in range(len(idx_path) - 1):
                            u_i = idx_path[ii]
                            v_i = idx_path[ii + 1]
                            rate = rate_map.get((u_i, v_i))
                            if rate is None or rate <= 0:
                                return None
                            p *= rate
                        return p

                    prod_fw = _prod_for_idx_fb(closed_idx)
                    rev_idx = list(reversed(closed_idx))
                    prod_rev = _prod_for_idx_fb(rev_idx)
                    # pick best available
                    prod = None
                    orientation = "forward"
                    if prod_fw is None and prod_rev is None:
                        prod = None
                    elif prod_rev is not None and (prod_fw is None or prod_rev > prod_fw):
                        prod = prod_rev
                        closed_idx = rev_idx
                        orientation = "reverse"
                    else:
                        prod = prod_fw
                        orientation = "forward"

                    hops = len(closed_idx) - 1
                    net_pct = (prod - 1.0) * 100.0 if prod is not None else None
                    net_bps = (prod - 1.0) * 10000.0 if prod is not None else None
                    filter_reasons = []
                    # hops filters
                    if min_hops and hops < min_hops:
                        filter_reasons.append("min_hops")
                    if max_hops and hops > max_hops:
                        filter_reasons.append("max_hops")
                    if prod is None:
                        filter_reasons.append("invalid_product")
                    elif net_pct is not None and net_pct < min_net:
                        filter_reasons.append("min_net")
                    if min_net_per_hop and net_pct is not None and (net_pct / max(1, hops)) < min_net_per_hop:
                        filter_reasons.append("min_net_per_hop")
                    # blacklist check
                    blocked = False
                    if blacklist:
                        try:
                            bl_idx = set()
                            for p in blacklist:
                                if isinstance(p, str) and "->" in p:
                                    a_s, b_s = p.split("->", 1)
                                    a_i = idx.get(a_s)
                                    b_i = idx.get(b_s)
                                    if a_i is not None and b_i is not None:
                                        bl_idx.add((a_i, b_i))
                        except Exception:
                            bl_idx = set()
                        for i in range(len(closed_idx) - 1):
                            if (closed_idx[i], closed_idx[i + 1]) in bl_idx:
                                blocked = True
                                filter_reasons.append("blacklist")
                                break

                    # Log every candidate cycle before filtering
                    candidate_entry = {
                        "ts": ts_now,
                        "venue": ex_id,
                        "cycle": "->".join([nodes[i] for i in closed_idx]),
                        "orientation": orientation,
                        "net_bps_est": round(net_bps - latency_penalty, 4) if net_bps is not None else None,
                        "fee_bps_total": round(hops * fee * 1.0, 6),
                        "hops": hops,
                        "status": "filtered" if filter_reasons else "actionable",
                        "filter_reasons": filter_reasons,
                    }
                    if candidate_log_path:
                        try:
                            with open(candidate_log_path, "a", encoding="utf-8") as cfh:
                                import json
                                cfh.write(json.dumps(candidate_entry) + "\n")
                        except Exception:
                            pass


                    # Configurable: return all cycles if bf.log_all_cycles is set
                    log_all_cycles = bool(cfg.get("bf", {}).get("log_all_cycles", False))
                    if log_all_cycles or not filter_reasons:
                        results.append(candidate_entry)
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
        # allow specific techniques to run inline (skip ProcessPool) for low-latency
        inline_set = set(cfg.get("techniques", {}).get("inline", []))
        for name in enabled:
            func = _TECHS.get(name)
            if not func:
                logger.warning("Technique %s not found; skipping", name)
                continue
            # If configured to run inline, execute directly to avoid IPC/pickling overhead.
            if name in inline_set:
                try:
                    start_ts = time.time()
                    res = func(snapshot_id, edges, cfg)
                    dur = time.time() - start_ts
                    # emit per-scan telemetry line if configured
                    try:
                        telemetry_file = cfg.get("techniques", {}).get("telemetry_file")
                        if telemetry_file:
                            with open(telemetry_file, "a", encoding="utf-8") as tfh:
                                payload = {
                                    "snapshot_id": snapshot_id,
                                    "technique": name,
                                    "timestamp": int(time.time()),
                                    "duration_s": dur,
                                    "results_count": len(res) if res else 0,
                                }
                                # include technique-specific telemetry if present
                                try:
                                    tech_tel = getattr(func, "_last_telemetry", None)
                                    if tech_tel:
                                        payload.update(tech_tel)
                                except Exception:
                                    pass
                                tfh.write(json.dumps(payload) + "\n")
                    except Exception:
                        logger.debug("failed to write per-scan telemetry for %s", name)
                    stats.setdefault(name, {"count": 0.0, "total_time": 0.0})
                    stats[name]["count"] += len(res) if res else 0.0
                    stats[name]["total_time"] += dur
                    if res:
                        results.extend(res)
                except Exception:
                    logger.exception("Inline technique %s failed", name)
                    # fall back to submitting to pool below
                    fut = pool.submit(func, snapshot_id, edges, cfg)
                    futures.append(fut)
                    future_map[fut] = (name, time.time())
                    stats.setdefault(name, {"count": 0.0, "total_time": 0.0})
                # continue to next technique
                continue

            fut = pool.submit(func, snapshot_id, edges, cfg)
            futures.append(fut)
            # record submit time to approximate worker duration
            future_map[fut] = (name, time.time())
            # init stats
            stats.setdefault(name, {"count": 0.0, "total_time": 0.0})

            # Use wait + FIRST_COMPLETED to avoid blocking indefinitely when a submitted
            # process hangs. If no future completes within the configured fallback
            # timeout, attempt fallbacks (for bellman_ford) or cancel long-running
            # tasks. This ensures timeouts actually fire instead of waiting forever
            # on as_completed.
            pending = set(futures)
            # timeout used to detect stuck technique workers; default to cfg.fallback_timeout
            global_timeout = float(
                cfg.get("techniques", {}).get("fallback_timeout", 5.0)
            )
            while pending:
                done, pending = wait(
                    pending, timeout=global_timeout, return_when=FIRST_COMPLETED
                )
                if not done:
                    # nothing completed within timeout -> handle pending tasks
                    for fut in list(pending):
                        name, submit_ts = future_map.get(fut, ("unknown", time.time()))
                        logger.warning(
                            "Technique %s did not complete within %.2fs; attempting fallback/cancel",
                            name,
                            global_timeout,
                        )
                        # Attempt fallback for bellman_ford specifically
                        if name == "bellman_ford":
                            fb_timeout = float(
                                cfg.get("techniques", {}).get("fallback_timeout", 5.0)
                            )
                            try:
                                with ThreadPoolExecutor(max_workers=1) as thpool:
                                    fb_future = thpool.submit(
                                        _tech_bellman_ford, snapshot_id, edges, cfg
                                    )
                                    fb_res = fb_future.result(timeout=fb_timeout)
                                    fb_dur = (
                                        time.time() - submit_ts if submit_ts else 0.0
                                    )
                                    logger.warning(
                                        "bellman_ford fallback produced %d results (timeout %.2fs)",
                                        len(fb_res) if fb_res else 0,
                                        fb_timeout,
                                    )
                                    stats.setdefault(
                                        name, {"count": 0.0, "total_time": 0.0}
                                    )
                                    stats[name]["count"] += (
                                        len(fb_res) if fb_res else 0.0
                                    )
                                    stats[name]["total_time"] += fb_dur
                                    if fb_res:
                                        results.extend(fb_res)
                                    telemetry_counters["fallback_count"] += 1
                            except ThreadTimeoutError:
                                logger.warning(
                                    "bellman_ford fallback timed out after %.2fs",
                                    fb_timeout,
                                )
                                telemetry_counters["fallback_timeouts"] += 1
                            except Exception:
                                logger.exception("bellman_ford fallback also failed")
                            # Try to cancel the original pending future to avoid resource leak.
                            # Even if cancel() returns False for a running ProcessPool future,
                            # remove it from the pending set so we don't loop forever waiting
                            # on an un-cancellable task.
                            try:
                                fut.cancel()
                            except Exception:
                                pass
                            # remove from pending and cleanup map so wait() won't see it again
                            try:
                                pending.discard(fut)
                            except Exception:
                                pass
                            future_map.pop(fut, None)
                        else:
                            # No generic fallback; cancel the pending future and continue
                            try:
                                fut.cancel()
                            except Exception:
                                pass
                    # continue loop to wait for any remaining done tasks
                    continue

                # Process completed futures
                for f in done:
                    name, submit_ts = future_map.get(f, ("unknown", time.time()))
                    start_wait = submit_ts
                    end_wait = time.time()
                    duration = max(0.0, end_wait - start_wait)
                    try:
                        # This should not block because f is in done
                        res = f.result()
                        # emit per-scan telemetry line if configured
                        try:
                            telemetry_file = cfg.get("techniques", {}).get(
                                "telemetry_file"
                            )
                            if telemetry_file:
                                with open(telemetry_file, "a", encoding="utf-8") as tfh:
                                    tfh.write(
                                        json.dumps(
                                            {
                                                "snapshot_id": snapshot_id,
                                                "technique": name,
                                                "timestamp": int(time.time()),
                                                "duration_s": duration,
                                                "results_count": len(res) if res else 0,
                                            }
                                        )
                                        + "\n"
                                    )
                        except Exception:
                            logger.debug(
                                "failed to write per-scan telemetry for %s", name
                            )
                        # update stats
                        stats.setdefault(name, {"count": 0.0, "total_time": 0.0})
                        stats[name]["count"] += len(res) if res else 0.0
                        stats[name]["total_time"] += duration
                        if res:
                            results.extend(res)
                    except Exception:
                        logger.exception(
                            "Technique task %s failed; attempting fallback if available",
                            name,
                        )
                        # safe fallback for bellman_ford: run in a thread with timeout to avoid blocking
                        if name == "bellman_ford":
                            fb_timeout = float(
                                cfg.get("techniques", {}).get("fallback_timeout", 5.0)
                            )
                            try:
                                with ThreadPoolExecutor(max_workers=1) as thpool:
                                    fb_future = thpool.submit(
                                        _tech_bellman_ford, snapshot_id, edges, cfg
                                    )
                                    fb_res = fb_future.result(timeout=fb_timeout)
                                    fb_dur = (
                                        time.time() - submit_ts if submit_ts else 0.0
                                    )
                                    logger.warning(
                                        "bellman_ford fallback produced %d results (timeout %.2fs)",
                                        len(fb_res) if fb_res else 0,
                                        fb_timeout,
                                    )
                                    stats.setdefault(
                                        name, {"count": 0.0, "total_time": 0.0}
                                    )
                                    stats[name]["count"] += (
                                        len(fb_res) if fb_res else 0.0
                                    )
                                    stats[name]["total_time"] += fb_dur
                                    if fb_res:
                                        results.extend(fb_res)
                                    telemetry_counters["fallback_count"] += 1
                            except ThreadTimeoutError:
                                logger.warning(
                                    "bellman_ford fallback timed out after %.2fs",
                                    fb_timeout,
                                )
                                telemetry_counters["fallback_timeouts"] += 1
                            except Exception:
                                logger.exception("bellman_ford fallback also failed")
                        else:
                            logger.warning(
                                "No fallback implemented for technique %s", name
                            )

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
            logger.info(
                "scan_arbitrage summary: techniques=%s results=%d payload_bytes=%d",
                list(stats.keys()),
                len(results),
                size_bytes,
            )
            for nm, s in stats.items():
                logger.info(
                    "tech=%s result_count=%s total_time=%.3fs",
                    nm,
                    int(s.get("count") or 0),
                    float(s.get("total_time") or 0.0),
                )
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
