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
from typing import Callable, Dict, List, Any

logger = logging.getLogger("arbitraje.engine_techniques")

try:
    # prefer project paths helper if available to resolve absolute artifact root
    from . import paths as _local_paths

    ARTIFACTS_ROOT = _local_paths.ARTIFACTS_ROOT
except Exception:
    ARTIFACTS_ROOT = None

# Types are expected to match project types; use light aliases to avoid heavy imports
Edge = object


class ArbResult(dict):
    """Minimal ArbResult container (dict-like) to remain compatible with callers."""


# --- Technique stubs (users will later map these to real implementations) ---
def _tech_bellman_ford(
    snapshot_id: str, edges: List[Edge], cfg: Dict
) -> List[ArbResult]:
    import datetime

    diag_log_path = None
    try:
        diag_log_path = str(
            Path(__file__).resolve().parents[1]
            / "artifacts"
            / "arbitraje"
            / "diagnostics.log"
        )
    except Exception:
        diag_log_path = None

    def diag_log(msg):
        ts_line = f"[{datetime.datetime.utcnow().isoformat()}] {msg}\n"
        wrote = False
        attempted = []
        # primary: if ARTIFACTS_ROOT is available, write to absolute artifacts path
        if ARTIFACTS_ROOT is not None:
            try:
                abs_diag = Path(ARTIFACTS_ROOT) / "diagnostics.log"
                abs_diag.parent.mkdir(parents=True, exist_ok=True)
                with open(abs_diag, "a", encoding="utf-8") as dfh:
                    dfh.write(ts_line)
                wrote = True
                attempted.append({"path": str(abs_diag), "ok": True, "err": None})
            except Exception as e:
                attempted.append(
                    {"path": str(ARTIFACTS_ROOT), "ok": False, "err": str(e)}
                )
                logger.debug(
                    "diag_log: failed to write absolute ARTIFACTS_ROOT diag=%s err=%s",
                    ARTIFACTS_ROOT,
                    e,
                )

        # primary: src/artifacts path (legacy)
        if diag_log_path:
            try:
                Path(diag_log_path).parent.mkdir(parents=True, exist_ok=True)
                with open(diag_log_path, "a", encoding="utf-8") as dfh:
                    dfh.write(ts_line)
                wrote = True
                attempted.append({"path": str(diag_log_path), "ok": True, "err": None})
            except Exception as e:
                attempted.append(
                    {"path": str(diag_log_path), "ok": False, "err": str(e)}
                )
                logger.debug(
                    "diag_log: failed to write primary diag_path=%s err=%s",
                    diag_log_path,
                    e,
                )

        # secondary: try project-level artifacts (parents[2]/artifacts/...)
        try:
            proj_diag_p = (
                Path(__file__).resolve().parents[2]
                / "artifacts"
                / "arbitraje"
                / "diagnostics.log"
            )
            proj_diag = str(proj_diag_p)
            if not wrote:
                try:
                    proj_diag_p.parent.mkdir(parents=True, exist_ok=True)
                    with open(proj_diag, "a", encoding="utf-8") as pfh:
                        pfh.write(ts_line)
                    wrote = True
                    attempted.append({"path": proj_diag, "ok": True, "err": None})
                except Exception as e:
                    attempted.append({"path": proj_diag, "ok": False, "err": str(e)})
                    logger.debug(
                        "diag_log: failed to write proj_diag=%s err=%s", proj_diag, e
                    )
        except Exception as e:
            logger.debug("diag_log: proj_diag resolution failed: %s", e)

        # tertiary: workspace-level artifacts (top-level workspace artifacts/arbitraje)
        if not wrote:
            try:
                ws_diag_p = (
                    Path(__file__).resolve().parents[3]
                    / "artifacts"
                    / "arbitraje"
                    / "diagnostics.log"
                )
                ws_diag = str(ws_diag_p)
                ws_diag_p.parent.mkdir(parents=True, exist_ok=True)
                with open(ws_diag, "a", encoding="utf-8") as wfh:
                    wfh.write(ts_line)
                wrote = True
                attempted.append({"path": ws_diag, "ok": True, "err": None})
            except Exception as e:
                attempted.append(
                    {
                        "path": locals().get("ws_diag", "<unknown>"),
                        "ok": False,
                        "err": str(e),
                    }
                )
                logger.debug(
                    "diag_log: failed to write workspace-level diag=%s err=%s",
                    locals().get("ws_diag", "<unknown>"),
                    e,
                )

        # Quiet mode: do not emit DIAG prints to stdout/logger here to avoid clutter.
        # Diagnostics are persisted to files (path-dump + diagnostics.log) for CI inspection.

        # Persist a canonical path-dump JSONL entry into the monorepo ARTIFACTS_ROOT
        path_dump_entry = {
            "ts": int(time.time()),
            "msg": msg,
            "attempted": attempted,
            "wrote": wrote,
        }
        try:
            if ARTIFACTS_ROOT is not None:
                pd = Path(ARTIFACTS_ROOT) / "diag_paths.jsonl"
            else:
                pd = (
                    Path(__file__).resolve().parents[2]
                    / "artifacts"
                    / "arbitraje"
                    / "diag_paths.jsonl"
                )
            pd.parent.mkdir(parents=True, exist_ok=True)
            with open(pd, "a", encoding="utf-8") as pfh:
                pfh.write(json.dumps(path_dump_entry) + "\n")
            # Rotate / truncate the JSONL if it grows too large to avoid unbounded growth
            try:
                # Conservative limits: keep last MAX_LINES or trim when file > MAX_BYTES
                MAX_BYTES = 5 * 1024 * 1024  # 5 MB
                MAX_LINES = 10000

                def _tail_lines_binary(path: Path, max_lines: int):
                    # Read file from end in binary and return last max_lines as a list of bytes lines
                    lines = []
                    with open(path, "rb") as fh:
                        fh.seek(0, os.SEEK_END)
                        file_size = fh.tell()
                        block_size = 4096
                        data = bytearray()
                        while file_size > 0 and len(lines) <= max_lines:
                            read_size = min(block_size, file_size)
                            fh.seek(file_size - read_size)
                            chunk = fh.read(read_size)
                            data = chunk + data
                            lines = data.splitlines()
                            file_size -= read_size
                            if file_size == 0:
                                break
                        # Ensure we return at most max_lines entries
                        if len(lines) > max_lines:
                            return lines[-max_lines:]
                        return lines

                try:
                    st = pd.stat()
                    if st.st_size > MAX_BYTES:
                        # Read last MAX_LINES lines and rewrite file atomically
                        tail = _tail_lines_binary(pd, MAX_LINES)
                        tmp = pd.with_suffix(".tmp")
                        with open(tmp, "wb") as outfh:
                            if tail:
                                outfh.write(b"\n".join(tail) + b"\n")
                        try:
                            os.replace(str(tmp), str(pd))
                        except Exception:
                            # best-effort: if rename fails, remove tmp
                            try:
                                tmp.unlink(missing_ok=True)
                            except Exception:
                                pass
                except Exception:
                    # If stat/read fails, ignore rotation for now
                    pass
            except Exception:
                # Keep diag logging robust: swallow any rotation errors
                pass
        except Exception as e:
            logger.debug("diag_log: failed to write diag_paths.jsonl: %s", e)

        # Duplicate a compact diagnostics.log entry to src artifacts for local debugging
        try:
            src_diag = (
                Path(__file__).resolve().parents[1]
                / "artifacts"
                / "arbitraje"
                / "diagnostics.log"
            )
            src_diag.parent.mkdir(parents=True, exist_ok=True)
            with open(src_diag, "a", encoding="utf-8") as sdf:
                sdf.write(ts_line)
        except Exception:
            pass

        # fallback: if neither file write succeeded, append to telemetry file if configured
        if not wrote:
            try:
                telemetry_file = cfg.get("techniques", {}).get("telemetry_file")
                if telemetry_file:
                    # Resolve relative telemetry_file paths to project-level (parents[2])
                    try:
                        tfp = Path(telemetry_file)
                        if not tfp.is_absolute():
                            tfp = Path(__file__).resolve().parents[2] / telemetry_file
                        tfp.parent.mkdir(parents=True, exist_ok=True)
                        with open(tfp, "a", encoding="utf-8") as tfh:
                            tfh.write(
                                json.dumps({"diagnostic": msg, "ts": int(time.time())})
                                + "\n"
                            )
                    except Exception:
                        logger.debug(
                            "diag_log: failed to write telemetry fallback to %s",
                            telemetry_file,
                        )
            except Exception:
                pass

    # If edges is a JSON string (we now submit JSON string), parse it into dict
    try:
        if isinstance(edges, str):
            try:
                edges = json.loads(edges)
            except Exception:
                # leave as string if parsing fails
                pass
    except Exception:
        pass

    # Worker-side diagnostic: record the payload byte-size to detect IPC/pickle losses
    try:
        import json as _json

        try:
            payload_bytes = len(_json.dumps(edges or {}))
        except Exception:
            payload_bytes = None
        if payload_bytes is not None:
            diag_log(f"Worker received payload_bytes={payload_bytes}")
        else:
            diag_log("Worker received payload_bytes=unknown")
    except Exception:
        pass

    t0 = time.time()
    logger.debug("_tech_bellman_ford running snapshot=%s", snapshot_id)
    try:
        # Expect a payload dict with tickers and tokens to avoid any network IO here.
        # Be defensive: callers may pass None or partial payloads; treat those
        # gracefully and return an empty result rather than raising.
        if not edges:
            logger.debug("_tech_bellman_ford received empty edges; skipping")
            return []

        # Prefer dict payloads. If it's not a mapping, skip (callers must pass dict/json)
        if not isinstance(edges, dict):
            logger.debug(
                "_tech_bellman_ford received non-dict edges (%s); skipping",
                type(edges),
            )
            return []
        else:
            payload = edges

        # If a precomputed volatility map is attached to the payload, use it.
        # This avoids recalculating stddevs inside the hot loop repeatedly.
        pre_vol = None
        try:
            pre_vol = payload.get("_precomputed_volatility")
        except Exception:
            pre_vol = None

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
                if (
                    (t.get("bid") and float(t.get("bid")) > 0)
                    or (t.get("ask") and float(t.get("ask")) > 0)
                    or (t.get("last") and float(t.get("last")) > 0)
                ):
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

        # Safe casters to avoid type-check/runtime issues when values are missing/None
        def _f(x, dv=0.0):
            try:
                if x is None:
                    return float(dv)
                return float(x)
            except Exception:
                return float(dv)

        def _i(x, dv=0):
            try:
                if x is None:
                    return int(dv)
                return int(x)
            except Exception:
                return int(dv)

        fee_val = _pick("fee", float, None)
        if fee_val is None:
            fee_val = payload.get("fee")
        fee = _f(fee_val, 0.0)
        # min_net is expressed in percent (e.g. 0.15 -> 0.15%)
        min_net = _f(_pick("min_net", float, None), 0.0)
        ts_now = payload.get("ts") or snapshot_id
        ex_id = payload.get("ex_id")
        tokens_val = _pick("tokens", list, None)
        if not tokens_val:
            tokens_val = payload.get("tokens") or []
        # ensure tokens are strings
        tokens = [str(t) for t in list(tokens_val)]
        top_n = _i(_pick("top", int, None), payload.get("top") or 20)
        min_hops = _i(_pick("min_hops", int, None), payload.get("min_hops") or 0)
        max_hops = _i(_pick("max_hops", int, None), payload.get("max_hops") or 0)
        min_net_per_hop = _f(_pick("min_net_per_hop", float, None), 0.0)
        latency_penalty = _f(_pick("latency_penalty", float, None), 0.0)
        bl_val = _pick("blacklist", list, None)
        if bl_val is None:
            bl_val = payload.get("blacklist") or []
        blacklist = set([str(b) for b in list(bl_val)])

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
        # (dump_graph intentionally executed after BF config/locals are populated)

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
            candidate_log_path = str(
                Path(__file__).resolve().parents[1]
                / "artifacts"
                / "arbitraje"
                / "candidate_cycles.log"
            )
        except Exception:
            candidate_log_path = None

        # Attempt to use Numba-accelerated BF if available (faster numeric core)
        use_numba = bool(cfg.get("techniques", {}).get("use_numba", True))
        try:
            # bf_numba_impl provides: bellman_ford_numba, build_arrays_from_payload
            from .bf_numba_impl import (
                bellman_ford_numba,
                build_arrays_from_payload,
            )
        except Exception:
            bellman_ford_numba = None
            build_arrays_from_payload = None

        # Prepare arrays for numeric BF
        u_arr = [u for (u, v, w) in edge_list]
        v_arr = [v for (u, v, w) in edge_list]
        w_arr = [w for (u, v, w) in edge_list]

        # Diagnostic: log edge list size before pruning
        diag_log(f"Edge list before pruning: nodes={n}, edges={len(edge_list)}")

        # Optional debug dump: persist the constructed graph, nodes and rate_map
        try:
            dump_graph_flag = bool(cfg.get("techniques", {}).get("dump_graph", False))
        except Exception:
            dump_graph_flag = False
        if dump_graph_flag:
            try:
                art_dir = (
                    Path(__file__).resolve().parents[1] / "artifacts" / "arbitraje"
                )
                art_dir.mkdir(parents=True, exist_ok=True)
                dump_path = art_dir / f"graph_debug_{str(int(time.time()))}.jsonl"
                # Compose a compact serializable structure
                dump_obj = {
                    "snapshot_id": snapshot_id,
                    "timestamp": int(time.time()),
                    "nodes": list(nodes),
                    "edge_list": [
                        [nodes[u], nodes[v], float(w)] for (u, v, w) in edge_list
                    ],
                    "rate_map": {
                        "%s->%s" % (nodes[u], nodes[v]): float(rate_map[(u, v)])
                        for (u, v) in list(rate_map.keys())
                    },
                    "cfg_filters": {
                        "fee": fee,
                        "min_net": min_net,
                        "min_quote_vol": (
                            payload.get("min_quote_vol")
                            if isinstance(payload, dict)
                            else None
                        ),
                        "latency_penalty": latency_penalty,
                    },
                }
                with open(dump_path, "a", encoding="utf-8") as dfh:
                    dfh.write(json.dumps(dump_obj) + "\n")
                diag_log(f"Wrote graph debug to {dump_path}")
            except Exception:
                logger.exception("failed to write graph debug dump")

        if bellman_ford_numba is not None and use_numba:
            try:
                # Optional warm-up (compile) to amortize JIT overhead at startup
                # optional warmup removed (function not guaranteed to exist)

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
                    diag_log(
                        f"After degree pruning: sources={len(sources) if sources else 0}"
                    )

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
                        diag_log(
                            f"After qvol pruning: sources={len(sources) if sources else 0}, k={k}, qvol_threshold_frac={qvol_threshold_frac}"
                        )

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
                    # normalize and ensure iterable of ints
                    if not isinstance(cycle_idx, (list, tuple)):
                        # unsupported structure; skip
                        continue
                    cycle_idx_int: list[int] = []
                    _ok = True
                    for x in cycle_idx:
                        # Guard against nested lists/tuples which are not valid indices
                        if isinstance(x, (list, tuple, dict)):
                            _ok = False
                            break
                        try:
                            xi = int(x)
                        except Exception:
                            _ok = False
                            break
                        cycle_idx_int.append(xi)
                    if not _ok or not cycle_idx_int:
                        continue
                    cycle_idx = cycle_idx_int
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
                    results.append(ArbResult(rec))
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
                # Persist worker return for debug (helps detect IPC/pickle loss)
                try:
                    dbg_dir = (
                        Path(__file__).resolve().parents[1] / "artifacts" / "arbitraje"
                    )
                    dbg_dir.mkdir(parents=True, exist_ok=True)
                    dbg_path = dbg_dir / "worker_return_debug.log"
                    with dbg_path.open("a", encoding="utf-8") as wfh:
                        wfh.write(
                            json.dumps(
                                {
                                    "snapshot_id": snapshot_id,
                                    "path": "numba_postproc",
                                    "results_count": len(results),
                                    "sample": results[:3],
                                }
                            )
                            + "\n"
                        )
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
            if diag_enabled and build_arrays_from_payload is not None:
                try:
                    # Use the available array builder and simple python array BF from bf_numba_impl if present
                    import importlib

                    bfmod = importlib.import_module("arbitraje.bf_numba_impl")
                    bf_array = getattr(bfmod, "bellman_ford_array", None)
                    if callable(bf_array):
                        nodes2, ua, va, wa = build_arrays_from_payload(payload)
                        arr_cycles = bf_array(len(nodes2), ua, va, wa)
                        if arr_cycles:
                            try:
                                smp = (
                                    arr_cycles[:3]
                                    if isinstance(arr_cycles, (list, tuple))
                                    else None
                                )
                            except Exception:
                                smp = None
                            logger.warning(
                                "Diagnostic BF-array found cycles (sample): %s",
                                smp,
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
                    elif prod_rev is not None and (
                        prod_fw is None or prod_rev > prod_fw
                    ):
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
                    if (
                        min_net_per_hop
                        and net_pct is not None
                        and (net_pct / max(1, hops)) < min_net_per_hop
                    ):
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
                        "net_bps_est": (
                            round(net_bps - latency_penalty, 4)
                            if net_bps is not None
                            else None
                        ),
                        "fee_bps_total": round(hops * fee * 1.0, 6),
                        "hops": hops,
                        "status": "filtered" if filter_reasons else "actionable",
                        "filter_reasons": filter_reasons,
                    }
                    if candidate_log_path:
                        try:
                            with open(candidate_log_path, "a", encoding="utf-8") as cfh:
                                cfh.write(json.dumps(candidate_entry) + "\n")
                        except Exception:
                            pass

                    # Configurable: return all cycles if bf.log_all_cycles is set
                    log_all_cycles = bool(
                        cfg.get("bf", {}).get("log_all_cycles", False)
                    )
                    if log_all_cycles or not filter_reasons:
                        results.append(ArbResult(candidate_entry))
                        if len(results) >= top_n:
                            return results

        # Persist worker return for debug (helps detect IPC/pickle loss)
        try:
            dbg_dir = Path(__file__).resolve().parents[1] / "artifacts" / "arbitraje"
            dbg_dir.mkdir(parents=True, exist_ok=True)
            dbg_path = dbg_dir / "worker_return_debug.log"
            with dbg_path.open("a", encoding="utf-8") as wfh:
                wfh.write(
                    json.dumps(
                        {
                            "snapshot_id": snapshot_id,
                            "path": "python_bf",
                            "results_count": len(results),
                            "sample": results[:3],
                        }
                    )
                    + "\n"
                )
        except Exception:
            pass
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
        # Accept JSON-serialized payloads (string) from ProcessPool submissions
        if isinstance(edges, str):
            try:
                edges = json.loads(edges)
            except Exception:
                # If parsing fails, keep as-is and skip below
                pass
        # If edges is a dict payload (preferred), unpack it
        if isinstance(edges, dict):
            payload = edges
            ex_id = payload.get("ex_id")
            quote = str(payload.get("quote") or "")
            tokens = [str(t) for t in (payload.get("tokens") or [])]
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
            import time as _time

            # Precompute maps
            r1_map = {}
            r3_map = {}
            for tkn in tokens:
                r1_map[tkn] = get_rate_and_qvol_local(quote, tkn)
                r3_map[tkn] = get_rate_and_qvol_local(tkn, quote)

            # Optional budget: prefer payload-specific, else techniques config
            time_budget = 0.0
            try:
                time_budget = float(payload.get("time_budget_sec") or 0.0)
            except Exception:
                time_budget = 0.0
            if not time_budget:
                try:
                    time_budget = float(
                        cfg.get("techniques", {}).get("tri_time_budget_sec", 0.0)
                        or 0.0
                    )
                except Exception:
                    time_budget = 0.0
            _start = _time.time()
            for X, Y in permutations(tokens, 2):
                if time_budget and (_time.time() - _start) >= time_budget:
                    break
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
                    results.append(ArbResult(rec))
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
    # Determine inline configuration early and take a fast path for BF-only
    inline_set = set(cfg.get("techniques", {}).get("inline", []))
    try:
        logger.debug(
            "scan_arbitrage: enabled=%s inline=%s max_workers=%s",
            enabled,
            list(inline_set),
            maxw,
        )
    except Exception:
        pass
    # Fast path: if only bellman_ford is enabled and runs inline, avoid ProcessPool entirely
    try:
        if set(enabled) == {"bellman_ford"} and ("bellman_ford" in inline_set or not inline_set):
            func = _TECHS.get("bellman_ford")
            if func:
                start_ts = time.time()
                res = func(snapshot_id, edges, cfg)
                dur = time.time() - start_ts
                try:
                    telemetry_file = cfg.get("techniques", {}).get("telemetry_file")
                    if telemetry_file:
                        with open(telemetry_file, "a", encoding="utf-8") as tfh:
                            tfh.write(
                                json.dumps(
                                    {
                                        "snapshot_id": snapshot_id,
                                        "technique": "bellman_ford_inline",
                                        "timestamp": int(time.time()),
                                        "duration_s": dur,
                                        "results_count": len(res) if res else 0,
                                    }
                                )
                                + "\n"
                            )
                except Exception:
                    pass
                return res or []
    except Exception:
        # Fall through to ProcessPool path on any error
        pass

    # Reuse or create the pool (do not recreate per call; expensive on Windows spawn)
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
    except Exception:
        inline_set = set()
        # In unit tests (pytest), default to running all techniques inline to avoid
        # pickling/IPC variability across platforms and ensure deterministic results.
        try:
            if os.environ.get("PYTEST_CURRENT_TEST"):
                inline_set = set(enabled)
        except Exception:
            pass

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
            # proceed to next technique
            continue

        # Prepare a sanitized, JSON-friendly payload for worker submission to
        # avoid pickling non-serializable objects (ccxt objects, custom types).
        try:
            # record original tickers count for diagnostics (before sanitization)
            try:
                orig_tickers_count = (
                    len(edges.get("tickers", {})) if isinstance(edges, dict) else 0
                )
            except Exception:
                orig_tickers_count = 0
            if isinstance(edges, dict):
                pw = {
                    "ex_id": edges.get("ex_id"),
                    "ts": edges.get("ts"),
                    "quote": edges.get("quote"),
                    "tokens": list(edges.get("tokens") or []),
                    "tickers": {},
                    "fee": float(edges.get("fee") or 0.0),
                    "min_net": float(edges.get("min_net") or 0.0),
                    "min_quote_vol": float(edges.get("min_quote_vol") or 0.0),
                    "latency_penalty": float(edges.get("latency_penalty") or 0.0),
                }
                for sym, t in (edges.get("tickers") or {}).items():
                    try:
                        pw_t = {}
                        if t is None or not isinstance(t, dict):
                            pw_t = {}
                        else:
                            b = t.get("bid")
                            a = t.get("ask")
                            l = t.get("last")
                            qv = (
                                t.get("quoteVolume")
                                or t.get("quoteVolume24h")
                                or t.get("volumeQuote")
                                or 0.0
                            )
                            if b is not None:
                                pw_t["bid"] = float(b)
                            if a is not None:
                                pw_t["ask"] = float(a)
                            if l is not None:
                                pw_t["last"] = float(l)
                            try:
                                pw_t["quoteVolume"] = float(qv or 0.0)
                            except Exception:
                                pw_t["quoteVolume"] = 0.0
                        pw["tickers"][sym] = pw_t
                    except Exception:
                        pw["tickers"][sym] = {}
            else:
                pw = edges
        except Exception:
            pw = edges

            # Write a tiny pre-submit diagnostic to help detect IPC/pickle issues
            try:
                # primary src/artifacts location
                art_dir = (
                    Path(__file__).resolve().parents[1] / "artifacts" / "arbitraje"
                )
                art_dir.mkdir(parents=True, exist_ok=True)
                diag_path = art_dir / "diagnostics.log"
                ts_line = None
                try:
                    # compute a conservative count of valid tickers (have bid/ask/last)
                    raw_tickers = pw.get("tickers", {}) if isinstance(pw, dict) else {}
                    valid_count = 0
                    def _pos(x: Any) -> bool:
                        if x is None:
                            return False
                        if isinstance(x, (int, float)):
                            try:
                                return float(x) > 0.0
                            except Exception:
                                return False
                        if isinstance(x, str):
                            try:
                                return float(x.strip()) > 0.0
                            except Exception:
                                return False
                        return False
                    try:
                        for v in (raw_tickers or {}).values():
                            if not v or not isinstance(v, dict):
                                continue
                            b = v.get("bid")
                            a = v.get("ask")
                            l = v.get("last")
                            if _pos(b) or _pos(a) or _pos(l):
                                valid_count += 1
                    except Exception:
                        valid_count = 0
                    pb = json.dumps(pw)
                    ex_ctx = str(pw.get("ex_id") or "") if isinstance(pw, dict) else ""
                    ts_line = f"[{time.strftime('%Y-%m-%dT%H:%M:%S')}] Pre-submit {name} ex={ex_ctx} snap={snapshot_id}: orig_tickers={orig_tickers_count} sanitized_tickers={valid_count}, payload_bytes={len(pb)}\n"
                except Exception:
                    ex_ctx = str(pw.get("ex_id") or "") if isinstance(pw, dict) else ""
                    # best-effort fallback line
                    ts_line = f"[{time.strftime('%Y-%m-%dT%H:%M:%S')}] Pre-submit {name} ex={ex_ctx} snap={snapshot_id}: tickers=unknown, payload_bytes=unknown\n"
                wrote = False
                try:
                    with open(diag_path, "a", encoding="utf-8") as dfh:
                        dfh.write(ts_line)
                    wrote = True
                except Exception:
                    wrote = False
                # secondary: project-level artifacts (one level up)
                try:
                    proj_diag = (
                        Path(__file__).resolve().parents[2]
                        / "artifacts"
                        / "arbitraje"
                        / "diagnostics.log"
                    )
                    proj_diag.parent.mkdir(parents=True, exist_ok=True)
                    if not wrote:
                        try:
                            with open(proj_diag, "a", encoding="utf-8") as pfh:
                                pfh.write(ts_line)
                            wrote = True
                        except Exception:
                            wrote = wrote or False
                except Exception:
                    pass
                # fallback: append a small diagnostic entry into the telemetry file if configured
                if not wrote:
                    try:
                        telemetry_file = cfg.get("techniques", {}).get("telemetry_file")
                        if telemetry_file:
                            with open(telemetry_file, "a", encoding="utf-8") as tfh:
                                tfh.write(
                                    json.dumps(
                                        {"diagnostic": ts_line, "ts": int(time.time())}
                                    )
                                    + "\n"
                                )
                    except Exception:
                        pass
            except Exception:
                pass

            # Ensure a minimal, compact telemetry/diagnostic entry is persisted
            try:
                telemetry_file = cfg.get("techniques", {}).get("telemetry_file")
                if telemetry_file:
                    tfp = Path(telemetry_file)
                    if not tfp.is_absolute():
                        tfp = Path(__file__).resolve().parents[2] / telemetry_file
                    tfp.parent.mkdir(parents=True, exist_ok=True)
                    short = {
                        "pre_submit": name,
                        "tickers": (len(pw.get("tickers", {})) if isinstance(pw, dict) else 0),
                        "ts": int(time.time()),
                    }
                    with open(tfp, "a", encoding="utf-8") as tfh:
                        tfh.write(json.dumps(short) + "\n")
            except Exception:
                logger.debug("Failed to write compact pre-submit telemetry")

        # If there are zero tickers in the sanitized payload, skip submitting to the ProcessPool
        try:
            # use the conservative valid_count above if available, otherwise fall back
            if isinstance(pw, dict):
                n_tickers = (
                    valid_count if "valid_count" in locals() else len(pw.get("tickers", {}))
                )
            else:
                n_tickers = 0
        except Exception:
            n_tickers = 0
        try:
            print(
                f"[PARENT] pre-submit technique={name} ex={pw.get('ex_id') if isinstance(pw, dict) else ''} orig_tickers={orig_tickers_count} sanitized_tickers={n_tickers}"
            )
        except Exception:
            pass
        if n_tickers == 0:
            logger.debug(
                "Skipping submit for technique %s: zero valid tickers in payload (ex=%s snap=%s)",
                name,
                str(pw.get("ex_id") if isinstance(pw, dict) else ""),
                snapshot_id,
            )
            # don't submit an empty payload to worker processes
            continue
        # Submit a JSON string payload to avoid pickling complex objects
        try:
            payload_str = json.dumps(pw)
        except Exception:
            # fallback to original object if serialization fails
            payload_str = pw

        fut = None
        try:
            fut = pool.submit(func, snapshot_id, payload_str, cfg)
            futures.append(fut)
            # record submit time to approximate worker duration
            future_map[fut] = (name, time.time())
            try:
                print(f"[PARENT] submitted technique={name} future={repr(fut)}")
            except Exception:
                pass
            # Persist a compact submission record so we can inspect future objects
            try:
                abs_dbg = Path(
                    r"c:\Users\Lenovo\dataqbs_IA\artifacts\arbitraje"
                )
                abs_dbg.mkdir(parents=True, exist_ok=True)
                sub_path = abs_dbg / "parent_future_submissions.log"
                with sub_path.open("a", encoding="utf-8") as sfh:
                    sfh.write(
                        json.dumps(
                            {
                                "snapshot_id": snapshot_id,
                                "technique": name,
                                "future_repr": repr(fut),
                                "ts": int(time.time()),
                            }
                        )
                        + "\n"
                    )
            except Exception:
                logger.debug("failed to write parent future submission debug")
        except Exception:
            logger.exception(
                "Failed to submit technique %s to process pool; attempting fallback submit",
                name,
            )
            try:
                # try submitting the original edges as a last-resort
                fut = pool.submit(func, snapshot_id, edges, cfg)
                futures.append(fut)
                future_map[fut] = (name, time.time())
            except Exception:
                logger.exception(
                    "Fallback submit also failed for technique %s; skipping",
                    name,
                )
            # init stats
            stats.setdefault(name, {"count": 0.0, "total_time": 0.0})

    # Use wait + FIRST_COMPLETED to avoid blocking indefinitely when a submitted
    # process hangs. If no future completes within the configured fallback
    # timeout, attempt fallbacks (for bellman_ford) or cancel long-running
    # tasks. This ensures timeouts actually fire instead of waiting forever
    # on as_completed.
    pending = set(futures)
    global_timeout = float(
        cfg.get("techniques", {}).get("fallback_timeout", 5.0)
    )
    # Ensure a sane default watchdog to prevent unbounded waits
    iter_watchdog = float(
        cfg.get("techniques", {}).get("iteration_watchdog_sec", 15.0) or 15.0
    )
    loop_start = time.time()
    _fallback_attempted = set()
    while pending:
        # hard watchdog to avoid infinite waits
        if iter_watchdog and (time.time() - loop_start) >= iter_watchdog:
            logger.error(
                "scan_arbitrage watchdog fired after %.2fs; cancelling %d pending",
                iter_watchdog,
                len(pending),
            )
            for fut in list(pending):
                try:
                    fut.cancel()
                except Exception:
                    pass
                future_map.pop(fut, None)
            pending.clear()
            break

        done, pending = wait(
            pending, timeout=global_timeout, return_when=FIRST_COMPLETED
        )
        if not done:
            # nothing completed within timeout -> handle pending tasks
            for fut in list(pending):
                tech_name, submit_ts = future_map.get(
                    fut, ("unknown", time.time())
                )
                logger.warning(
                    "Technique %s did not complete within %.2fs; attempting fallback/cancel",
                    tech_name,
                    global_timeout,
                )
                if tech_name == "bellman_ford":
                    fb_timeout = float(
                        cfg.get("techniques", {}).get("fallback_timeout", 5.0)
                    )
                    if fut not in _fallback_attempted:
                        _fallback_attempted.add(fut)
                        try:
                            with ThreadPoolExecutor(max_workers=1) as thpool:
                                fb_future = thpool.submit(
                                    _tech_bellman_ford, snapshot_id, edges, cfg
                                )
                                fb_res = fb_future.result(timeout=fb_timeout)
                                fb_dur = (
                                    (time.time() - submit_ts) if submit_ts else 0.0
                                )
                                logger.warning(
                                    "bellman_ford fallback produced %d results (timeout %.2fs)",
                                    len(fb_res) if fb_res else 0,
                                    fb_timeout,
                                )
                                stats.setdefault(
                                    tech_name, {"count": 0.0, "total_time": 0.0}
                                )
                                stats[tech_name]["count"] += (
                                    len(fb_res) if fb_res else 0.0
                                )
                                stats[tech_name]["total_time"] += fb_dur
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
                # cancel the original pending future and drop it
                try:
                    fut.cancel()
                except Exception:
                    pass
                future_map.pop(fut, None)
                try:
                    pending.remove(fut)
                except Exception:
                    pass
            # continue to wait for any remaining futures
            continue

        # Process completed futures
        for f in done:
                    tech_name, submit_ts = future_map.get(f, ("unknown", time.time()))
                    duration = max(0.0, time.time() - (submit_ts or time.time()))
                    fut_done = None
                    fut_cancelled = None
                    fut_repr = None
                    fut_exc = None
                    res = None
                    try:
                        try:
                            fut_done = f.done()
                        except Exception:
                            pass
                        try:
                            fut_cancelled = f.cancelled()
                        except Exception:
                            pass
                        try:
                            fut_repr = repr(f)
                        except Exception:
                            pass
                        # before-result state
                        try:
                            abs_dbg = Path(
                                r"c:\Users\Lenovo\dataqbs_IA\artifacts\arbitraje"
                            )
                            abs_dbg.mkdir(parents=True, exist_ok=True)
                            abs_path = abs_dbg / "parent_future_debug.log"
                            with abs_path.open("a", encoding="utf-8") as afh:
                                afh.write(
                                    json.dumps(
                                        {
                                            "action": "pre_result",
                                            "snapshot_id": snapshot_id,
                                            "technique": tech_name,
                                            "future_done": fut_done,
                                            "future_cancelled": fut_cancelled,
                                            "future_repr": fut_repr,
                                            "ts": int(time.time()),
                                        }
                                    )
                                    + "\n"
                                )
                        except Exception:
                            pass
                        try:
                            res = f.result()
                        except Exception as e:
                            fut_exc = str(e)
                            res = None
                        # after-result state
                        try:
                            sample = res[:3] if isinstance(res, (list, tuple)) else res
                        except Exception:
                            sample = str(res)
                        try:
                            dbg_payload = {
                                "action": "post_result",
                                "snapshot_id": snapshot_id,
                                "technique": tech_name,
                                "future_done": fut_done,
                                "future_cancelled": fut_cancelled,
                                "future_repr": fut_repr,
                                "future_exception": fut_exc,
                                "results_count": len(res) if res else 0,
                                "sample": sample,
                                "ts": int(time.time()),
                            }
                            abs_dbg = Path(
                                r"c:\Users\Lenovo\dataqbs_IA\artifacts\arbitraje"
                            )
                            abs_dbg.mkdir(parents=True, exist_ok=True)
                            abs_path = abs_dbg / "parent_future_debug.log"
                            with abs_path.open("a", encoding="utf-8") as afh:
                                afh.write(json.dumps(dbg_payload) + "\n")
                        except Exception:
                            logger.debug(
                                "failed to write absolute parent future debug file"
                            )
                        stats.setdefault(tech_name, {"count": 0.0, "total_time": 0.0})
                        stats[tech_name]["count"] += len(res) if res else 0.0
                        stats[tech_name]["total_time"] += duration
                        if res:
                            results.extend(res)
                            try:
                                print(
                                    f"[PARENT] got results from {tech_name}: count={len(res)} sample={repr(res[:2])}"
                                )
                            except Exception:
                                pass
                    except Exception:
                        logger.exception(
                            "Technique task %s failed; attempting fallback if available",
                            tech_name,
                        )
                        if tech_name == "bellman_ford":
                            fb_timeout = float(
                                cfg.get("techniques", {}).get("fallback_timeout", 5.0)
                            )
                            try:
                                with ThreadPoolExecutor(max_workers=1) as thpool:
                                    fb_future = thpool.submit(
                                        _tech_bellman_ford, snapshot_id, edges, cfg
                                    )
                                    fb_res = fb_future.result(timeout=fb_timeout)
                                    fb_dur = time.time() - (submit_ts or time.time())
                                    logger.warning(
                                        "bellman_ford fallback produced %d results (timeout %.2fs)",
                                        len(fb_res) if fb_res else 0,
                                        fb_timeout,
                                    )
                                    stats.setdefault(
                                        tech_name, {"count": 0.0, "total_time": 0.0}
                                    )
                                    stats[tech_name]["count"] += (
                                        len(fb_res) if fb_res else 0.0
                                    )
                                    stats[tech_name]["total_time"] += fb_dur
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
                                "No fallback implemented for technique %s", tech_name
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
