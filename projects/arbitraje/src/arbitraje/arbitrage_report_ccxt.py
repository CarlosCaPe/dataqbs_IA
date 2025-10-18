from __future__ import annotations

# ...existing code...


# Ejecuta main() si el archivo es ejecutado como script

# (esto debe ir al final del archivo para evitar NameError)


import argparse
import json
import logging
import math
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

import ccxt  # type: ignore
import pandas as pd
import yaml
from tabulate import tabulate

from . import paths

try:
    # ...existing code...
    import ujson as _json  # optional faster JSON serializer
except Exception:
    _json = None

from . import binance_api  # type: ignore

# Shared simulation state used by TRI/BF simulation helpers (hydrated at runtime)
sim_state: Dict[str, dict] = {}


# Forward-stub: real implementation appears later in the file. Stub satisfies linters
def _sync_snapshot_alias() -> None:  # real def overrides this later
    return


try:
    from dotenv import load_dotenv

    load_dotenv(dotenv_path=str(paths.MONOREPO_ROOT / ".env"), override=False)
    load_dotenv(dotenv_path=str(paths.PROJECT_ROOT / ".env"), override=False)
except Exception:
    pass

try:
    from .ws_binance import BinanceL2PartialBook  # type: ignore
except Exception:
    BinanceL2PartialBook = None  # type: ignore

logger = logging.getLogger("arbitraje_ccxt")
if not logger.handlers:
    # Allow overriding the default logging level via environment variables
    # ARBITRAJE_LOG_LEVEL or LOGLEVEL (e.g. DEBUG, INFO). If not set, default to INFO.
    level_str = os.environ.get("ARBITRAJE_LOG_LEVEL") or os.environ.get("LOGLEVEL")
    try:
        level = getattr(logging, str(level_str).upper()) if level_str else logging.INFO
        if not isinstance(level, int):
            level = logging.INFO
    except Exception:
        level = logging.INFO
    logger.setLevel(level)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    logger.addHandler(sh)
    try:
        # Also set the root logger level so other arbitraje modules (engine_techniques, etc.)
        # that use their own loggers will emit at the requested level during debugging.
        logging.getLogger().setLevel(level)
    except Exception:
        pass
    try:
        paths.LOGS_DIR.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(
            paths.LOGS_DIR / "arbitraje_ccxt.log", encoding="utf-8"
        )
        fh.setFormatter(fmt)
        logger.addHandler(fh)
    except Exception:
        pass

# Common stable-coin bases used for filtering in INTER mode
STABLE_BASES = {"USDT", "USDC", "BUSD", "TUSD", "FDUSD", "DAI", "USTC"}


# ----------------------
# Helpers (env/ccxt)
# ----------------------
def env_get_stripped(name: str) -> str | None:
    try:
        v = os.environ.get(name)
        if v is None:
            return None
        return v.strip()
    except Exception:
        return os.environ.get(name)


def safe_has(ex: ccxt.Exchange, feature: str) -> bool:
    try:
        return bool(ex.has.get(feature))
    except Exception:
        return False


def load_exchange(ex_id: str, timeout_ms: int) -> ccxt.Exchange:
    ex_id = (ex_id or "").strip().lower()
    cls = getattr(ccxt, ex_id)
    ex = cls({"enableRateLimit": True})
    try:
        ex.timeout = int(timeout_ms)
    except Exception:
        pass
    return ex


def creds_from_env(ex_id: str) -> dict:
    ex = (ex_id or "").strip().lower()
    try:
        if ex == "binance":
            k = env_get_stripped("BINANCE_API_KEY")
            s = env_get_stripped("BINANCE_API_SECRET")
            if k and s:
                return {"apiKey": k, "secret": s}
        elif ex == "bybit":
            k = env_get_stripped("BYBIT_API_KEY")
            s = env_get_stripped("BYBIT_API_SECRET")
            if k and s:
                return {"apiKey": k, "secret": s}
        elif ex == "bitget":
            k = env_get_stripped("BITGET_API_KEY")
            s = env_get_stripped("BITGET_API_SECRET")
            p = env_get_stripped("BITGET_PASSWORD")
            if k and s and p:
                return {"apiKey": k, "secret": s, "password": p}
        elif ex in ("gate", "gateio"):
            k = env_get_stripped("GATEIO_API_KEY") or env_get_stripped("GATE_API_KEY")
            s = env_get_stripped("GATEIO_API_SECRET") or env_get_stripped(
                "GATE_API_SECRET"
            )
            if k and s:
                return {"apiKey": k, "secret": s}
        elif ex == "coinbase":
            k = env_get_stripped("COINBASE_API_KEY")
            s = env_get_stripped("COINBASE_API_SECRET")
            p = env_get_stripped("COINBASE_API_PASSWORD")
            if k and s and p:
                return {"apiKey": k, "secret": s, "password": p}
        elif ex == "okx":
            k = env_get_stripped("OKX_API_KEY")
            s = env_get_stripped("OKX_API_SECRET")
            p = env_get_stripped("OKX_API_PASSWORD") or env_get_stripped("OKX_PASSWORD")
            if k and s and p:
                return {"apiKey": k, "secret": s, "password": p}
        elif ex == "kucoin":
            k = env_get_stripped("KUCOIN_API_KEY")
            s = env_get_stripped("KUCOIN_API_SECRET")
            p = env_get_stripped("KUCOIN_API_PASSWORD")
            if k and s and p:
                return {"apiKey": k, "secret": s, "password": p}
        elif ex == "kraken":
            k = env_get_stripped("KRAKEN_API_KEY")
            s = env_get_stripped("KRAKEN_API_SECRET")
            if k and s:
                return {"apiKey": k, "secret": s}
        elif ex == "mexc":
            k = env_get_stripped("MEXC_API_KEY")
            s = env_get_stripped("MEXC_API_SECRET")
            if k and s:
                return {"apiKey": k, "secret": s}
    except Exception:
        pass
    return {}


def load_exchange_auth_if_available(
    ex_id: str, timeout_ms: int, use_auth: bool = False
) -> ccxt.Exchange:
    """Load an exchange; if use_auth, pass credentials from env when available."""
    ex_id = normalize_ccxt_id(ex_id)
    cls = getattr(ccxt, ex_id)
    cfg = {"enableRateLimit": True}
    if use_auth:
        cfg.update(creds_from_env(ex_id))
    # Allow per-exchange options via env vars when useful
    if ex_id == "okx":
        try:
            # Prefer ARBITRAJE_OKX_DEFAULT_TYPE, fallback to OKX_DEFAULT_TYPE
            dt = os.environ.get("ARBITRAJE_OKX_DEFAULT_TYPE") or os.environ.get(
                "OKX_DEFAULT_TYPE"
            )
            if dt:
                opts = dict(cfg.get("options") or {})
                opts["defaultType"] = str(dt).strip().lower()
                cfg["options"] = opts
        except Exception:
            pass
    ex = cls(cfg)
    try:
        ex.timeout = int(timeout_ms)
    except Exception:
        pass
    return ex


def fetch_quote_balance(
    ex: ccxt.Exchange, quote: str, kind: str = "free"
) -> float | None:
    """Fetch QUOTE balance from an authenticated ccxt exchange instance. Returns None on error/missing."""
    try:
        bal = ex.fetch_balance()
        bucket = (
            bal.get("free") if (kind or "free").lower() == "free" else bal.get("total")
        )
        if not isinstance(bucket, dict):
            return None
        for ccy, amt in bucket.items():
            try:
                if str(ccy).upper() == str(quote).upper():
                    return float(amt)
            except Exception:
                continue
    except Exception:
        return None
    return None


def normalize_symbol(m: dict) -> Tuple[str, str]:
    base = str(m.get("base") or "").upper()
    quote = str(m.get("quote") or "").upper()
    return f"{base}/{quote}", base


def pct(sell: float, buy: float) -> float:
    try:
        return (float(sell) - float(buy)) / float(buy) * 100.0
    except Exception:
        return float("nan")


def fmt_price(x: float) -> str:
    s = f"{float(x):.8f}"
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return s


def get_rate_and_qvol(
    a: str,
    b: str,
    tickers: Dict[str, dict],
    fee_pct: float,
    require_topofbook: bool = False,
) -> Tuple[float | None, float | None]:
    """Return (rate, quote_volume) for converting a->b using top-of-book where possible.

    - If require_topofbook=True, do not fallback to 'last' when bid/ask missing.
    - quote_volume is taken from the market used (direct a/b or inverse b/a).
    """
    a = a.upper()
    b = b.upper()
    fee = float(fee_pct) / 100.0
    # direct A/B: selling A for B uses bid; qvol from that ticker
    sym1 = f"{a}/{b}"
    t1 = tickers.get(sym1)
    if t1:
        bid = t1.get("bid") if require_topofbook else (t1.get("bid") or t1.get("last"))
        if bid and bid > 0:
            qv = get_quote_volume(t1)
            return float(bid) * (1.0 - fee), qv
    # inverse B/A: buying B with A uses 1/ask
    sym2 = f"{b}/{a}"
    t2 = tickers.get(sym2)
    if t2:
        ask = t2.get("ask") if require_topofbook else (t2.get("ask") or t2.get("last"))
        if ask and ask > 0:
            qv = get_quote_volume(t2)
            return (1.0 / float(ask)) * (1.0 - fee), qv
    return None, None


def build_rates_for_exchange(
    currencies: List[str],
    tickers: Dict[str, dict],
    fee_pct: float,
    require_topofbook: bool = False,
    min_quote_vol: float = 0.0,
    blacklisted_symbols: set[str] | None = None,
) -> Tuple[List[Tuple[int, int, float]], Dict[Tuple[int, int], float]]:
    cur_index = {c: i for i, c in enumerate(currencies)}
    edges: List[Tuple[int, int, float]] = []
    rate_map: Dict[Tuple[int, int], float] = {}
    for u in currencies:
        for v in currencies:
            if u == v:
                continue
            if _pair_is_blacklisted(blacklisted_symbols, u, v):
                continue
            r, qv = get_rate_and_qvol(u, v, tickers, fee_pct, require_topofbook)
            if r and r > 0:
                if min_quote_vol > 0.0:
                    if qv is None or qv < min_quote_vol:
                        continue
                u_i = cur_index[u]
                v_i = cur_index[v]
                edges.append((u_i, v_i, -math.log(r)))
                rate_map[(u_i, v_i)] = r
    return edges, rate_map


def get_quote_volume(t: dict) -> float | None:
    for k in ("quoteVolume", "qvol", "volumeQuote"):
        v = t.get(k)
        if v is not None:
            try:
                return float(v)
            except Exception:
                pass
    info = t.get("info") or {}
    for k in ("quoteVolume", "Q", "quote_volume", "quoteTurnover", "volumeQuote"):
        v = info.get(k)
        if v is not None:
            try:
                return float(v)
            except Exception:
                pass
    return None


# ----------------------
# Simulation helpers
# ----------------------
def _prefetch_wallet_buckets(ex_ids: List[str], args) -> Dict[str, Dict[str, float]]:
    """Fetch balances once per exchange for the iteration when simulate_from_wallet is enabled.

    Returns a map: ex_id -> { currency: amount } for the requested balance kind (free/total).
    Exchanges without credentials or on error will be omitted.
    """
    buckets: Dict[str, Dict[str, float]] = {}
    try:
        if not getattr(args, "simulate_from_wallet", False):
            return buckets
        for ex_id in ex_ids:
            try:
                if not creds_from_env(ex_id):
                    continue
                ex_auth = load_exchange_auth_if_available(
                    ex_id, args.timeout, use_auth=True
                )
                bal_all = ex_auth.fetch_balance() or {}
                # Use 'total' balances for header visibility as requested
                bucket = bal_all.get("total") or {}
                cur_map: Dict[str, float] = {}
                for ccy, amt in (bucket or {}).items():
                    try:
                        val = float(amt or 0.0)
                    except Exception:
                        val = 0.0
                    if val and abs(val) > 0.0:
                        cur_map[str(ccy)] = val
                if cur_map:
                    buckets[ex_id] = cur_map
            except Exception:
                continue
    except Exception:
        pass
    return buckets


def _build_simulation_rows(
    sim_state: Dict[str, Dict[str, object]],
    args,
    wallet_buckets: Dict[str, Dict[str, float]],
) -> List[dict]:
    """Build rows for 'Simulación (estado actual)' without altering output format.

    - If wallet_buckets has data for an exchange, render one row per non-zero currency in that wallet.
    - Otherwise, render a single row with the simulation currency and balances from sim_state.
    """
    rows_sim: List[dict] = []
    if not sim_state:
        return rows_sim
    for ex_id, st in sim_state.items():
        try:
            start_bal = float(st.get("start_balance", 0.0) or 0.0)
        except Exception:
            start_bal = 0.0
        try:
            bal = float(st.get("balance", 0.0) or 0.0)
        except Exception:
            bal = 0.0
        ccy = str(st.get("ccy", ""))
        per_ccy_rows: List[dict] = []
        wbucket = wallet_buckets.get(ex_id)
        if getattr(args, "simulate_from_wallet", False) and wbucket:
            for ccy2, val in wbucket.items():
                try:
                    val_f = float(val or 0.0)
                except Exception:
                    val_f = 0.0
                if val_f and abs(val_f) > 0.0:
                    # If we don't know start per currency, show current as start
                    # when unknown. This keeps ROI at 0 unless a simulate start
                    # balance applies.
                    sb_disp = (
                        start_bal
                        if str(ccy2).upper() == str(ccy).upper() and start_bal > 0.0
                        else (val_f if start_bal == 0.0 else 0.0)
                    )
                    roi = ((val_f - sb_disp) / sb_disp * 100.0) if sb_disp > 0 else 0.0
                    per_ccy_rows.append(
                        {
                            "exchange": ex_id,
                            "currency": str(ccy2),
                            "start_balance": round(sb_disp, 8),
                            "balance": round(val_f, 8),
                            "profit": round(val_f - sb_disp, 8),
                            "roi_pct": round(roi, 6),
                        }
                    )
        if not per_ccy_rows:
            # Fallback: single row with current simulation currency
            sb_disp = start_bal
            if (
                getattr(args, "simulate_from_wallet", False)
                and sb_disp == 0.0
                and bal > 0.0
            ):
                sb_disp = bal
            roi = ((bal - sb_disp) / sb_disp * 100.0) if sb_disp > 0 else 0.0
            per_ccy_rows.append(
                {
                    "exchange": ex_id,
                    "currency": ccy,
                    "start_balance": round(sb_disp, 8),
                    "balance": round(bal, 8),
                    "profit": round(bal - sb_disp, 8),
                    "roi_pct": round(roi, 6),
                }
            )
        rows_sim.extend(per_ccy_rows)
    return rows_sim


# ----------------------
# Depth-aware utilities
# ----------------------
def _consume_depth(ob: dict, side: str, qty: float) -> tuple[float | None, float]:
    """Return (avg_px, slippage_bps) by consuming depth levels for a given quantity.

    - side = 'buy' uses asks; 'sell' uses bids
    - slippage estimated vs best level in bps
    """
    try:
        qty = float(qty)
    except Exception:
        return None, 0.0
    if qty <= 0:
        return None, 0.0
    levels = ob.get("asks") if side == "buy" else ob.get("bids")
    if not levels:
        return None, 0.0
    remaining = qty
    notional = 0.0
    filled = 0.0
    ref_px = float(levels[0][0]) if levels and levels[0] and levels[0][0] else None
    for px, q in levels:
        try:
            px = float(px)
            q = float(q)
        except Exception:
            continue
        take = min(remaining, q)
        notional += take * px
        filled += take
        remaining -= take
        if remaining <= 1e-15:
            break
    if filled <= 0:
        return None, 0.0
    avg_px = notional / filled
    slip_bps = 0.0
    try:
        if ref_px and avg_px:
            if side == "buy":
                slip_bps = max(0.0, (avg_px / ref_px - 1.0) * 10000.0)
            else:
                slip_bps = max(0.0, (1.0 - avg_px / ref_px) * 10000.0)
    except Exception:
        pass
    return avg_px, slip_bps


def _fetch_order_book(ex: ccxt.Exchange, sym: str, limit: int = 20) -> dict | None:
    try:
        return ex.fetch_order_book(sym, limit=limit)
    except Exception:
        return None


def _bf_revalidate_cycle_with_depth(
    ex: ccxt.Exchange,
    cycle_nodes: list[str],
    inv_quote: float,
    fee_bps_per_hop: float,
    depth_levels: int = 20,
    use_ws: bool = False,
    latency_penalty_bps: float = 0.0,
) -> tuple[float | None, float, float, bool]:
    """Safe stub for depth-aware revalidation; returns None to signal no adjustment."""
    try:
        hops = max(0, len(cycle_nodes) - 1)
        return None, float(fee_bps_per_hop) * float(hops), 0.0, False
    except Exception:
        return None, 0.0, 0.0, False


def normalize_ccxt_id(ex_id: str) -> str:
    """Map common aliases to ccxt canonical IDs (e.g., gateio->gate, okex->okx)."""
    x = (ex_id or "").lower().strip()
    aliases = {
        "gateio": "gate",
        "okex": "okx",
        "coinbasepro": "coinbase",
        "huobipro": "htx",
    }
    return aliases.get(x, x)


def _build_adjacency_from_markets(markets: dict) -> Dict[str, set]:
    """Build undirected adjacency: currency -> set(other currencies with a direct market)."""
    adj: Dict[str, set] = {}
    try:
        for s, m in (markets or {}).items():
            if not m.get("active", True):
                continue
            base = str(m.get("base") or "").upper()
            quote = str(m.get("quote") or "").upper()
            if not base or not quote:
                continue
            adj.setdefault(base, set()).add(quote)
            adj.setdefault(quote, set()).add(base)
    except Exception:
        pass
    return adj


def build_rates_for_exchange_from_pairs(
    currencies: List[str],
    tickers: Dict[str, dict],
    fee_pct: float,
    candidate_pairs: List[Tuple[str, str]],
    require_topofbook: bool = False,
    min_quote_vol: float = 0.0,
    blacklisted_symbols: set[str] | None = None,
) -> Tuple[List[Tuple[int, int, float]], Dict[Tuple[int, int], float]]:
    """Faster edge builder using only existing market pairs.

    candidate_pairs is a list of directed pairs (u, v) where either u/v or v/u exists in markets.
    """
    cur_index = {c: i for i, c in enumerate(currencies)}
    edges: List[Tuple[int, int, float]] = []
    rate_map: Dict[Tuple[int, int], float] = {}
    for u, v in candidate_pairs:
        if u == v:
            continue
        if _pair_is_blacklisted(blacklisted_symbols, u, v):
            continue
        r, qv = get_rate_and_qvol(u, v, tickers, fee_pct, require_topofbook)
        if r and r > 0:
            if min_quote_vol > 0.0:
                if qv is None or qv < min_quote_vol:
                    continue
            u_i = cur_index.get(u)
            v_i = cur_index.get(v)
            if u_i is None or v_i is None:
                continue
            edges.append((u_i, v_i, -math.log(r)))
            rate_map[(u_i, v_i)] = r
    return edges, rate_map


def _normalize_pair(symbol: str) -> str | None:
    try:
        s = str(symbol or "").strip()
    except Exception:
        return None
    if not s:
        return None
    s = s.replace("-", "/").replace("_", "/").upper()
    if "/" not in s:
        return None
    base, quote = [p.strip() for p in s.split("/", 1)]
    if not base or not quote:
        return None
    return f"{base}/{quote}"


def _expand_path_to_pairs(path: str) -> List[str]:
    try:
        nodes = [n.strip().upper() for n in path.split("->") if n.strip()]
    except Exception:
        return []
    pairs: List[str] = []
    for a, b in zip(nodes, nodes[1:]):
        norm = _normalize_pair(f"{a}/{b}")
        if norm:
            pairs.append(norm)
    return pairs


def _pair_is_blacklisted(symbols: set[str] | None, a: str, b: str) -> bool:
    if not symbols:
        return False
    pair = _normalize_pair(f"{a}/{b}")
    if pair and pair in symbols:
        return True
    inverse = _normalize_pair(f"{b}/{a}")
    if inverse and inverse in symbols:
        return True
    return False


def _add_blacklist_entry(dst: Dict[str, set[str]], exchange: str, symbol: str) -> None:
    if not exchange or not symbol:
        return
    sym = _normalize_pair(symbol)
    if not sym:
        return

    ex_norm = normalize_ccxt_id(exchange)
    bucket = dst.setdefault(ex_norm, set())
    bucket.add(sym)


def _collect_blacklist_values(
    dst: Dict[str, set[str]], value, source: str, exchange_hint: str | None = None
) -> None:
    if value is None:
        return
    if isinstance(value, str):
        val = value.strip()
        if not val:
            return
        if "->" in val and "/" not in val:
            for pair in _expand_path_to_pairs(val):
                if exchange_hint:
                    _add_blacklist_entry(dst, exchange_hint, pair)
            return
        if ":" in val and exchange_hint is None:
            ex_part, sym_part = val.split(":", 1)
            _collect_blacklist_values(dst, sym_part, source, ex_part)
            return
        if exchange_hint is None:
            return
        _add_blacklist_entry(dst, exchange_hint, val)
        return
    if isinstance(value, (list, tuple, set)):
        for item in value:
            _collect_blacklist_values(dst, item, source, exchange_hint)
        return
    if isinstance(value, dict):
        for ex_key, sub in value.items():
            _collect_blacklist_values(dst, sub, source, str(ex_key))


def _ensure_blacklist_json_contains(
    json_path: Path, required: Dict[str, set[str]]
) -> None:
    if not required:
        return
    try:
        data = {}
        if json_path.exists():
            with open(json_path, "r", encoding="utf-8") as fh:
                data = json.load(fh) or {}
    except Exception:
        data = {}
    pairs = {}
    if isinstance(data, dict):
        pairs = data.get("pairs") if isinstance(data.get("pairs"), dict) else data
        if not isinstance(pairs, dict):
            pairs = {}
    else:
        pairs = {}
    changed = False
    now = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    for ex, symbols in required.items():
        for sym in symbols:
            key = f"{normalize_ccxt_id(ex)}:{sym.lower()}"
            if key not in pairs:
                pairs[key] = {"reason": "config_import", "added_at": now}
                changed = True
    if changed:
        payload = {"pairs": pairs}
        try:
            json_path.parent.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
        with open(json_path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, sort_keys=True)


def load_swaps_blacklist() -> Dict[str, set[str]]:
    json_path = paths.LOGS_DIR / "swapper_blacklist.json"
    manual_entries: Dict[str, set[str]] = {}
    for cfg_name in ("swapper.yaml", "swapper.live.yaml"):
        cfg_path = paths.PROJECT_ROOT / cfg_name
        if not cfg_path.exists():
            continue
        try:
            with open(cfg_path, "r", encoding="utf-8") as fh:
                cfg_raw = yaml.safe_load(fh) or {}
        except Exception:
            continue
        if not isinstance(cfg_raw, dict):
            continue
        for key in (
            "blacklist_pairs",
            "blacklisted_pairs",
            "banned_pairs",
            "static_blacklist",
            "manual_blacklist",
        ):
            if key in cfg_raw:
                _collect_blacklist_values(manual_entries, cfg_raw.get(key), key)
    _ensure_blacklist_json_contains(json_path, manual_entries)

    combined: Dict[str, set[str]] = {}
    try:
        if json_path.exists():
            with open(json_path, "r", encoding="utf-8") as fh:
                data = json.load(fh) or {}
        else:
            data = {}
    except Exception:
        data = {}
    pairs_section = {}
    if isinstance(data, dict):
        pairs_section = (
            data.get("pairs") if isinstance(data.get("pairs"), dict) else data
        )
    if not isinstance(pairs_section, dict):
        pairs_section = {}
    for key, meta in pairs_section.items():
        if not isinstance(key, str):
            continue
        if ":" not in key:
            continue
        ex_part, sym_part = key.split(":", 1)
        _add_blacklist_entry(combined, ex_part, sym_part)
    for ex, symbols in manual_entries.items():
        for sym in symbols:
            _add_blacklist_entry(combined, ex, sym)
    return combined


def resolve_exchanges(arg: str, ex_limit: int | None = None) -> List[str]:
    arg = (arg or "").strip().lower()
    if not arg or arg == "trusted":
        return ["binance", "bitget", "bybit", "coinbase"]
    if arg in ("trusted-plus", "trusted_plus", "trustedplus"):
        return ["binance", "bitget", "bybit", "coinbase"]
    if arg == "all":
        xs = list(ccxt.exchanges)
        if ex_limit and ex_limit > 0:
            xs = xs[:ex_limit]
        return [normalize_ccxt_id(x) for x in xs]
    # explicit comma-separated list
    return [normalize_ccxt_id(s.strip().lower()) for s in arg.split(",") if s.strip()]


# ----------------------
# Main
# ----------------------
def _bf_quantile(sorted_vals, q: float) -> float:
    if not sorted_vals:
        return 0.0
    if q <= 0:
        return float(sorted_vals[0])
    if q >= 1:
        return float(sorted_vals[-1])
    idx = q * (len(sorted_vals) - 1)
    lo = int(idx)
    hi = min(lo + 1, len(sorted_vals) - 1)
    frac = idx - lo
    return float(sorted_vals[lo]) * (1 - frac) + float(sorted_vals[hi]) * frac


def _bf_parse_history_for_sim(path: str):
    import re
    from datetime import datetime

    # Capture the currency token (USDT/USDC/etc.) instead of hardcoding USDT
    sim_rx = re.compile(
        (
            r"^\[SIM\] it#(?P<it>\d+) @(?P<ex>\w+)\s+"
            r"(?P<ccy>[A-Z]{3,6}) pick .* net (?P<net>[\d\.]+)% \| "
            r"(?P<ccy2>[A-Z]{3,6}) (?P<u0>[\d\.]+) -> (?P<u1>[\d\.]+) "
            r"\(\+(?P<delta>[\d\.]+)\)"
        )
    )
    iter_ts_rx = re.compile(
        r"^\[BF\] Iteración \d+\/\d+ @ (?P<ts>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+\+\d{2}:\d{2})$"
    )

    trades = []
    first_ts = None
    last_ts = None

    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                s = line.rstrip("\n")
                m = sim_rx.match(s)
                if m:
                    ccy = m.group("ccy")
                    trades.append(
                        {
                            "ex": m.group("ex"),
                            "ccy": ccy,
                            "net": float(m.group("net")),
                            "u0": float(m.group("u0")),
                            "u1": float(m.group("u1")),
                            "delta": float(m.group("delta")),
                        }
                    )
                    continue
                tsm = iter_ts_rx.match(s)
                if tsm:
                    ts = tsm.group("ts")
                    try:
                        dt = datetime.fromisoformat(ts)
                    except Exception:
                        # Fallback: remove colon in offset
                        if ts[-3] == ":":
                            ts2 = ts[:-3] + ts[-2:]
                            dt = datetime.strptime(ts2, "%Y-%m-%dT%H:%M:%S.%f%z")
                        else:
                            raise
                    if first_ts is None:
                        first_ts = dt
                    last_ts = dt
    except Exception:
        return [], 0.0

    hours = 0.0
    if first_ts and last_ts:
        if first_ts.tzinfo is None:
            from datetime import timezone as _tz

            first_ts = first_ts.replace(tzinfo=_tz.utc)
        if last_ts.tzinfo is None:
            from datetime import timezone as _tz

            last_ts = last_ts.replace(tzinfo=_tz.utc)
        hours = (last_ts - first_ts).total_seconds() / 3600.0

    return trades, hours


def _bf_summarize_trades(trades, hours: float):
    from collections import defaultdict

    agg = defaultdict(
        lambda: {
            "nets": [],
            "sum_delta": 0.0,
            "sum_u0": 0.0,
            "n": 0,
            # Track first and last balances per currency; compute gains from end-start (not sum of deltas)
            "start_usdt": None,
            "end_usdt": None,
            "start_usdc": None,
            "end_usdc": None,
        }
    )
    for t in trades:
        ex = t.get("ex")
        ccy = (t.get("ccy") or "").upper()
        u0 = float(t.get("u0", 0.0))
        u1 = float(t.get("u1", 0.0))
        dlt = float(t.get("delta", 0.0))
        agg[ex]["nets"].append(float(t.get("net", 0.0)))
        agg[ex]["sum_delta"] += dlt
        agg[ex]["sum_u0"] += u0
        agg[ex]["n"] += 1
        if ccy == "USDT":
            # capture first starting balance and always update ending balance
            if agg[ex]["start_usdt"] is None:
                agg[ex]["start_usdt"] = u0
            agg[ex]["end_usdt"] = u1
        elif ccy == "USDC":
            if agg[ex]["start_usdc"] is None:
                agg[ex]["start_usdc"] = u0
            agg[ex]["end_usdc"] = u1

    rows = []
    for ex, a in agg.items():
        nets = sorted(a["nets"]) if a["nets"] else []
        n = int(a["n"])
        avg = (sum(nets) / n) if n else 0.0
        med = _bf_quantile(nets, 0.5) if n else 0.0
        p95 = _bf_quantile(nets, 0.95) if n else 0.0
        per_hour = (n / hours) if hours > 0 else 0.0
        weighted = (100.0 * (a["sum_delta"] / a["sum_u0"])) if a["sum_u0"] > 0 else 0.0
        # Realized gains must be derived from balance deltas to avoid double counting
        start_usdt = a["start_usdt"] if a["start_usdt"] is not None else 0.0
        end_usdt = a["end_usdt"] if a["end_usdt"] is not None else 0.0
        start_usdc = a["start_usdc"] if a["start_usdc"] is not None else 0.0
        end_usdc = a["end_usdc"] if a["end_usdc"] is not None else 0.0
        gain_usdt = (
            (end_usdt - start_usdt)
            if (a["start_usdt"] is not None and a["end_usdt"] is not None)
            else 0.0
        )
        gain_usdc = (
            (end_usdc - start_usdc)
            if (a["start_usdc"] is not None and a["end_usdc"] is not None)
            else 0.0
        )

        rows.append(
            {
                "exchange": ex,
                "trades": n,
                "per_hour": round(per_hour, 2),
                "avg_net_pct": round(avg, 4),
                "median_net_pct": round(med, 4),
                "p95_net_pct": round(p95, 4),
                "weighted_net_pct": round(weighted, 4),
                "total_delta": round(a["sum_delta"], 4),
                "sum_u0": round(a["sum_u0"], 4),
                # currency-aware outputs derived from balance deltas
                "gain_usdt": round(gain_usdt, 8),
                "gain_usdc": round(gain_usdc, 8),
                "start_usdt": round(start_usdt, 8),
                "end_usdt": round(end_usdt, 8),
                "start_usdc": round(start_usdc, 8),
                "end_usdc": round(end_usdc, 8),
            }
        )
    rows.sort(key=lambda r: r["trades"], reverse=True)
    return rows


def _bf_write_summary_csv(rows, out_csv: str) -> None:
    import os

    os.makedirs(os.path.dirname(out_csv), exist_ok=True)
    headers = [
        "exchange",
        "trades",
        "per_hour",
        "avg_net_pct",
        "median_net_pct",
        "p95_net_pct",
        "weighted_net_pct",
        "total_delta",
        "sum_u0",
        "gain_usdt",
        "gain_usdc",
        "start_usdt",
        "end_usdt",
        "start_usdc",
        "end_usdc",
    ]
    with open(out_csv, "w", encoding="utf-8") as f:
        f.write(",".join(headers) + "\n")
        for r in rows:
            f.write(",".join(str(r[h]) for h in headers) + "\n")


def _bf_write_summary_md(rows, hours: float, out_md: str) -> None:
    import os

    os.makedirs(os.path.dirname(out_md), exist_ok=True)
    total_trades = sum(r.get("trades", 0) for r in rows)
    with open(out_md, "w", encoding="utf-8") as f:
        f.write("# BF summary\n\n")
        f.write(f"Window: ~{hours:.2f} hours\n\n")
        f.write(f"Total picks: {total_trades}\n\n")
        f.write("## Per exchange\n\n")
        f.write(
            (
                "exchange | trades | per_hour | avg_net% | median_net% | p95_net% | "
                "weighted_net% | gain_usdt | gain_usdc | start_usdt | end_usdt | "
                "start_usdc | end_usdc\n"
            )
        )
        f.write("---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:\n")
        for r in rows:
            row_fields = [
                str(r.get("exchange")),
                str(r.get("trades")),
                str(r.get("per_hour")),
                str(r.get("avg_net_pct")),
                str(r.get("median_net_pct")),
                str(r.get("p95_net_pct")),
                str(r.get("weighted_net_pct")),
                str(r.get("gain_usdt")),
                str(r.get("gain_usdc")),
                str(r.get("start_usdt")),
                str(r.get("end_usdt")),
                str(r.get("start_usdc")),
                str(r.get("end_usdc")),
            ]
            f.write(" | ".join(row_fields) + "\n")


def _bf_write_history_summary_and_md(
    history_path: str, out_csv: str, out_md: str
) -> None:
    trades, hours = _bf_parse_history_for_sim(history_path)
    if not trades:
        return
    rows = _bf_summarize_trades(trades, hours)
    _bf_write_summary_csv(rows, out_csv)
    _bf_write_summary_md(rows, hours, out_md)


def _load_yaml_config_defaults(parser: argparse.ArgumentParser) -> None:
    """Load arbitraje.yaml (or --config/ARBITRAJE_CONFIG) and set parser defaults.

    Precedence: CLI > YAML > code defaults. YAML can use flat keys (matching
    arg names) and/or sections 'bf' and 'tri' which map to bf_* / tri_*.
    Lists for fields like 'ex' or 'bf.allowed_quotes' are converted to CSV.
    """
    try:
        prelim, _ = parser.parse_known_args()
        cfg_path_in = getattr(prelim, "config", None) or os.environ.get(
            "ARBITRAJE_CONFIG"
        )

        # Resolve YAML path robustly across different CWDs
        def _resolve_yaml_path(pth: str | None) -> str | None:
            if not pth:
                return None
            try:
                # 1) As provided (absolute or relative to CWD)
                if os.path.exists(pth):
                    return pth
                # 2) Relative to project root
                cand = str(paths.PROJECT_ROOT / pth)
                if os.path.exists(cand):
                    return cand
                # 3) Relative to monorepo root
                cand2 = str(paths.MONOREPO_ROOT / pth)
                if os.path.exists(cand2):
                    return cand2
            except Exception:
                pass
            return None

        cfg_path = _resolve_yaml_path(cfg_path_in)
        if not cfg_path:
            # Fallback to default arbitraje.yaml in project root
            cfg_path = str(paths.PROJECT_ROOT / "arbitraje.yaml")
            if not os.path.exists(cfg_path):
                try:
                    logger.warning(
                        "Config YAML no encontrado: %s (CWD=%s). Usando defaults.",
                        cfg_path_in,
                        os.getcwd(),
                    )
                except Exception:
                    pass
                return

        # Load YAML with a fallback that normalizes leading tabs to spaces if parsing fails
        try:
            with open(cfg_path, "r", encoding="utf-8") as fh:
                raw = yaml.safe_load(fh) or {}
        except Exception as e_yaml:
            # Retry by replacing leading tabs with two spaces only if tabs exist
            try:
                with open(cfg_path, "r", encoding="utf-8") as fh:
                    txt = fh.read()
                has_tabs = "\t" in txt
                # Replace tabs that appear as indentation at start of lines
                sanitized_lines = []
                if has_tabs:
                    for line in txt.splitlines(True):  # keepends
                        i = 0
                        while i < len(line) and line[i] == "\t":
                            i += 1
                        if i > 0:
                            line = ("  " * i) + line[i:]
                        sanitized_lines.append(line)
                    sanitized = "".join(sanitized_lines)
                else:
                    sanitized = txt
                raw = yaml.safe_load(sanitized) or {}
                try:
                    if has_tabs:
                        logger.warning(
                            "Config YAML tenía tabs de indentación; se normalizó a espacios: %s",
                            cfg_path,
                        )
                    else:
                        logger.warning(
                            "Config YAML requería reintento de parseo: %s (err: %s)",
                            cfg_path,
                            e_yaml,
                        )
                except Exception:
                    pass
            except Exception:
                # Give up quietly and keep defaults
                return
        try:
            logger.info("Usando config YAML: %s", cfg_path)
        except Exception:
            pass
        conf: dict = {}

        def list_to_csv(v):
            if isinstance(v, list):
                return ",".join(str(x) for x in v)
            return v

        # Flat keys
        flat_keys = {
            "mode",
            "ex",
            "exclude_ex",
            "quote",
            "max",
            "timeout",
            "sleep",
            "inv",
            "top",
            "min_spread",
            "min_price",
            "include_stables",
            "min_sources",
            "min_quote_vol",
            "vol_strict",
            "max_spread_cap",
            "buy_fee",
            "sell_fee",
            "xfer_fee_pct",
            "per_ex_timeout",
            "per_ex_limit",
            "ex_limit",
            "repeat",
            "repeat_sleep",
            "console_clear",
            "no_console_clear",
            "simulate_compound",
            "simulate_start",
            "simulate_select",
            "simulate_from_wallet",
            "simulate_prefer",
            "simulate_auto_switch",
            "simulate_switch_threshold",
            "balance_provider",
            "ex_auth_only",
            # Preloading/network control
            "preload",
            # Offline controls (already supported as CLI flags, allow YAML too)
            "offline",
            "offline_snapshot",
            "bf_allowed_quotes",
            # UI options (flat)
            "ui_progress_bar",
            "ui_progress_len",
            "ui_spinner_frames",
            "ui_draw_tables_first",
        }
        for k in flat_keys:
            if k in raw:
                v = raw[k]
                if k in ("ex", "bf_allowed_quotes"):
                    v = list_to_csv(v)
                conf[k] = v

        # Sections
        for section, prefix in (
            (raw.get("bf") or {}, "bf_"),
            (raw.get("tri") or {}, "tri_"),
        ):
            pass
        bf = raw.get("bf", {}) or {}
        for k, v in bf.items():
            key = f"bf_{k}"
            if k in ("allowed_quotes",):
                v = list_to_csv(v)
            conf[key] = v
        tri = raw.get("tri", {}) or {}
        for k, v in tri.items():
            key = f"tri_{k}"
            conf[key] = v
        ui = raw.get("ui", {}) or {}
        for k, v in ui.items():
            key = f"ui_{k}"
            conf[key] = v

        if conf:
            parser.set_defaults(**conf)
    except Exception:
        # Ignore config errors, keep code defaults
        return


def main() -> None:
    # Startup health checks removed to avoid blocking network calls at startup.
    # The BF/TRI loops already log per-exchange timings and errors.
    parser = argparse.ArgumentParser(
        description="Arbitraje (ccxt) - modes: tri | bf | balance | health"
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="Print package and engine version and exit",
    )
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Path to YAML config file (CLI overrides YAML)",
    )
    parser.add_argument(
        "--mode", choices=["tri", "bf", "balance", "health"], default="bf"
    )
    parser.add_argument(
        "--ex",
        type=str,
        default="trusted",
        help="trusted | trusted-plus | all | comma list",
    )
    parser.add_argument(
        "--exclude_ex",
        type=str,
        default="",
        help="Comma-separated exchanges to exclude after resolution (e.g., 'bitso,bitstamp')",
    )
    parser.add_argument("--quote", type=str, default="USDT")
    parser.add_argument("--max", type=int, default=200, dest="max")
    parser.add_argument("--timeout", type=int, default=20000, help="ccxt timeout (ms)")
    parser.add_argument(
        "--sleep", type=float, default=0, help="sleep between requests (s)"
    )
    parser.add_argument("--inv", type=float, default=1000.0)
    parser.add_argument("--top", type=int, default=25)
    parser.add_argument(
        "--bf_reset_history",
        action="store_true",
        help="Borrar historial BF al inicio de la ejecución (bf_history.txt / history_bf.txt / HISTORY_BF.txt)",
    )

    # Inter-exchange filters and fees
    parser.add_argument("--min_spread", type=float, default=0.5)
    parser.add_argument("--min_price", type=float, default=0.0)
    parser.add_argument("--include_stables", action="store_true")
    parser.add_argument("--min_sources", type=int, default=2)
    parser.add_argument("--min_quote_vol", type=float, default=0.0)
    parser.add_argument("--vol_strict", action="store_true")
    parser.add_argument("--max_spread_cap", type=float, default=10.0)
    parser.add_argument("--buy_fee", type=float, default=0.10, help="%%")
    parser.add_argument("--sell_fee", type=float, default=0.10, help="%%")
    parser.add_argument(
        "--xfer_fee_pct", type=float, default=0.0, help="%% additional xfer cost"
    )
    parser.add_argument(
        "--per_ex_timeout",
        type=float,
        default=6.0,
        help="seconds per-exchange budget when iterating symbols",
    )
    parser.add_argument(
        "--per_ex_limit",
        type=int,
        default=0,
        help="max symbols per exchange iteration (0 = no cap)",
    )
    parser.add_argument(
        "--ex_limit", type=int, default=0, help="cap number of exchanges when ex=all"
    )

    # Triangular
    parser.add_argument("--tri_fee", type=float, default=0.10, help="per-hop fee %%")
    parser.add_argument("--tri_currencies_limit", type=int, default=35)
    parser.add_argument("--tri_min_net", type=float, default=0.5)
    parser.add_argument("--tri_top", type=int, default=5)
    parser.add_argument(
        "--tri_require_topofbook",
        action="store_true",
        help="Use only bid/ask; no 'last' fallback",
    )
    parser.add_argument(
        "--tri_time_budget_sec",
        type=float,
        default=0.0,
        help="Optional per-exchange time budget (seconds) for TRI scan; 0 disables",
    )
    parser.add_argument(
        "--tri_min_quote_vol",
        type=float,
        default=0.0,
        help="Filter hops by min quote volume",
    )

    # Bellman-Ford
    parser.add_argument("--bf_fee", type=float, default=0.10, help="per-hop fee %%")
    parser.add_argument("--bf_currencies_limit", type=int, default=35)
    parser.add_argument(
        "--bf_rank_by_qvol",
        action="store_true",
        help="Rank and select currencies by aggregate quote volume to build a higher-quality universe",
    )
    parser.add_argument("--bf_min_net", type=float, default=0.5)
    parser.add_argument(
        "--bf_min_net_per_hop",
        type=float,
        default=0.0,
        help="Descarta ciclos BF cuyo net/hop sea inferior a este umbral (%%)",
    )
    parser.add_argument("--bf_top", type=int, default=5)
    parser.add_argument(
        "--bf_persist_top_csv",
        action="store_true",
        help="Persistir las top oportunidades por iteración en un CSV acumulado",
    )
    parser.add_argument("--bf_require_quote", action="store_true")
    parser.add_argument("--bf_min_hops", type=int, default=0)
    parser.add_argument("--bf_max_hops", type=int, default=0)
    parser.add_argument(
        "--bf_require_topofbook",
        dest="bf_require_topofbook",
        action="store_true",
        help="Use only bid/ask; no 'last' fallback",
    )
    # Allow overriding YAML 'true' from CLI by providing an explicit negative flag
    parser.add_argument(
        "--no-bf_require_topofbook",
        dest="bf_require_topofbook",
        action="store_false",
        help="Allow 'last' fallback when bid/ask missing (overrides YAML)",
    )
    parser.add_argument(
        "--bf_min_quote_vol",
        type=float,
        default=0.0,
        help="Filter edges by min quote volume",
    )
    parser.add_argument(
        "--bf_threads",
        type=int,
        default=0,
        help="Threads for per-exchange BF scanning (1 = no threading, 0 or negative = one thread per exchange)",
    )
    parser.add_argument(
        "--bf_debug_list_triangles",
        action="store_true",
        help=(
            "DEBUG: en BF, listar también ciclos triangulares (USDT->X->Y->USDT) "
            "incluyendo nets negativos para calibración; rellena el CSV aunque no haya arbs BF"
        ),
    )
    parser.add_argument(
        "--bf_debug",
        action="store_true",
        help="Print BF debug details: currencies, edges, and cycles counts per exchange",
    )
    parser.add_argument(
        "--bf_require_dual_quote",
        action="store_true",
        help=(
            "When multiple anchors (e.g. USDT,USDC) are allowed, include only "
            "bases that have markets against ALL anchors"
        ),
    )
    # Depth-aware revalidation (optional)
    parser.add_argument(
        "--bf_revalidate_depth",
        dest="bf_revalidate_depth",
        action="store_true",
        help="Revalidar los ciclos BF con profundidad L2 (consume niveles) antes de reportar",
    )
    # Negative flag to disable depth revalidation even if YAML enables it
    parser.add_argument(
        "--no-bf_revalidate_depth",
        dest="bf_revalidate_depth",
        action="store_false",
        help="Desactivar revalidación con profundidad L2 (override YAML)",
    )
    parser.add_argument(
        "--bf_use_ws",
        action="store_true",
        help="Intentar usar WebSocket L2 parcial (solo binance por ahora); fallback REST si no disponible",
    )
    parser.add_argument(
        "--bf_depth_levels",
        type=int,
        default=20,
        help="Niveles de profundidad para REST fallback",
    )
    parser.add_argument(
        "--bf_latency_penalty_bps",
        type=float,
        default=0.0,
        help="Penalización de latencia (bps) restada al net%% estimado tras revalidación de profundidad",
    )
    parser.add_argument(
        "--bf_iter_timeout_sec",
        type=float,
        default=0.0,
        help="Tiempo máximo (segundos) para esperar resultados por iteración en BF; 0 = sin límite",
    )

    # BF simulation (compounding) across iterations
    parser.add_argument(
        "--simulate_compound",
        action="store_true",
        help=(
            "Simulate compounding: keep a running QUOTE balance and apply one "
            "selected BF opportunity per iteration (no real trades)"
        ),
    )
    parser.add_argument(
        "--simulate_start",
        type=float,
        default=None,
        help="Starting QUOTE balance for simulation (defaults to --inv if omitted)",
    )
    parser.add_argument(
        "--simulate_select",
        choices=["best", "first"],
        default="best",
        help="How to choose the opportunity each iteration: best = highest net %% ; first = first found",
    )
    parser.add_argument(
        "--simulate_from_wallet",
        action="store_true",
        help="Initialize simulation from wallet balance (USDT/USDC); requires exchange credentials",
    )
    parser.add_argument(
        "--simulate_prefer",
        choices=["USDT", "USDC", "auto"],
        default="auto",
        help="Preferred anchor when using --simulate_from_wallet; auto = choose with higher balance",
    )
    parser.add_argument(
        "--simulate_auto_switch",
        action="store_true",
        help="Auto-switch simulation anchor (USDT/USDC) to the currency with the best available cycle each iteration",
    )
    parser.add_argument(
        "--simulate_switch_threshold",
        type=float,
        default=0.0,
        help="Minimum additional net %% required to switch anchor vs current anchor's best (default 0.0)",
    )

    # Repeat / UX
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--repeat_sleep", type=float, default=0.0)
    parser.add_argument("--console_clear", action="store_true")
    parser.add_argument(
        "--no_console_clear",
        action="store_true",
        help="Don't clear console even if --console_clear is set (or set ARBITRAJE_NO_CLEAR=1)",
    )
    # UI / UX options for snapshot
    parser.add_argument(
        "--ui_progress_bar",
        action="store_true",
        default=True,
        help="Mostrar barra de progreso en current_bf.txt",
    )
    parser.add_argument(
        "--ui_progress_len",
        type=int,
        default=20,
        help="Longitud de la barra de progreso",
    )
    parser.add_argument(
        "--ui_spinner_frames",
        type=str,
        default="|/-\\",
        help="Frames del spinner para progreso en vivo",
    )
    parser.add_argument(
        "--ui_draw_tables_first",
        action="store_true",
        default=True,
        help="Dibujar tablas vacías desde el inicio de la iteración",
    )
    # Balance provider selection
    parser.add_argument(
        "--balance_provider",
        choices=["ccxt", "native", "connector", "bitget_sdk"],
        default="ccxt",
        help=(
            "Provider for --mode balance: ccxt (default), native (direct REST for "
            "binance), connector (official Binance SDK Spot), or bitget_sdk "
            "(official Bitget SDK)"
        ),
    )
    # Filter exchanges to only those with credentials
    parser.add_argument(
        "--ex_auth_only",
        action="store_true",
        help="Only include exchanges that have API credentials present in environment",
    )
    # Allow multiple anchor quotes (e.g., USDT and USDC)
    parser.add_argument(
        "--bf_allowed_quotes",
        type=str,
        default=None,
        help="Comma-separated list of allowed anchor quotes for BF cycles, e.g. 'USDT,USDC' (defaults to QUOTE only)",
    )

    # Offline / snapshot mode to avoid contacting live exchanges
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Run without contacting live exchanges; load tickers from --offline-snapshot if provided",
    )
    parser.add_argument(
        "--offline-snapshot",
        type=str,
        default=None,
        help="Path to a JSON file containing pre-captured tickers keyed by exchange id (optional)",
    )
    parser.add_argument(
        "--no-techniques-bf",
        action="store_true",
        help="Disable running BF via engine_techniques and use legacy in-process BF (for debugging)",
    )

    # Apply YAML defaults before parsing final args so CLI wins over YAML
    _load_yaml_config_defaults(parser)
    args = parser.parse_args()

    # If --version requested, print semver and engine label and exit early.
    if getattr(args, "version", False):
        try:
            # Read monorepo-wide pyproject for engine label, and project pyproject for package version
            root_pp = paths.MONOREPO_ROOT / "pyproject.toml"
            proj_pp = paths.PROJECT_ROOT / "pyproject.toml"
            engine_label = None
            pkg_version = None
            import tomllib

            try:
                with open(root_pp, "rb") as fh:
                    data = tomllib.load(fh)
                    engine_label = data.get("tool", {}).get("dataqbs", {}).get("engine")
            except Exception:
                engine_label = None
            try:
                with open(proj_pp, "rb") as fh:
                    data = tomllib.load(fh)
                    pkg_version = data.get("tool", {}).get("poetry", {}).get("version")
            except Exception:
                pkg_version = None
            print(
                f"arbitraje version: {pkg_version or 'unknown'}; engine: {engine_label or 'unknown'}"
            )
            return
        except Exception:
            print("version: unknown")
            return

    # If offline snapshot provided, load it once
    offline_snapshot_map: Dict[str, dict] | None = None
    if getattr(args, "offline", False) and getattr(args, "offline_snapshot", None):
        try:
            spath = Path(getattr(args, "offline_snapshot"))
            if spath.exists():
                with open(spath, "r", encoding="utf-8") as fh:
                    offline_snapshot_map = json.load(fh)
        except Exception:
            offline_snapshot_map = None

    # Load raw YAML config for runtime overrides (best-effort). We keep a map
    # exchange_overrides_map that maps exchange id -> overrides dict.
    cfg_raw: dict = {}
    try:
        cfg_path = (
            getattr(args, "config", None)
            or os.environ.get("ARBITRAJE_CONFIG")
            or str(paths.PROJECT_ROOT / "arbitraje.yaml")
        )
        try:
            with open(cfg_path, "r", encoding="utf-8") as fh:
                cfg_raw = yaml.safe_load(fh) or {}
        except Exception:
            cfg_raw = {}
    except Exception:
        cfg_raw = {}

    exchange_overrides_map: dict = {}
    try:
        if isinstance(cfg_raw, dict):
            eov = cfg_raw.get("exchange_overrides") or {}
            if isinstance(eov, dict):
                exchange_overrides_map = eov
    except Exception:
        exchange_overrides_map = {}

    def _apply_exchange_override(
        prefix: str, ex_id_local: str, arg_name: str, default_val
    ):
        """Return override value for a prefixed arg (e.g. prefix='tri_', arg_name='min_quote_vol').
        Supports two override styles:
        - exchange_overrides:
            <ex>:
              tri:
                min_quote_vol: 10
        - exchange_overrides with flat keys:
            <ex>:
              tri_min_quote_vol: 10
        """
        try:
            if not exchange_overrides_map:
                return default_val
            norm = normalize_ccxt_id(ex_id_local)
            ex_cfg = (
                exchange_overrides_map.get(norm)
                or exchange_overrides_map.get(ex_id_local)
                or {}
            )
            if not isinstance(ex_cfg, dict):
                return default_val
            # nested section
            section = ex_cfg.get(prefix.rstrip("_"))
            if isinstance(section, dict) and arg_name in section:
                return section.get(arg_name)
            # flat key: e.g. tri_min_quote_vol
            flat = f"{prefix}{arg_name}"
            if flat in ex_cfg:
                return ex_cfg.get(flat)
        except Exception:
            pass
        return default_val

    # Balance usage is unconditional now; we'll always try to use authenticated instances when creds exist.

    QUOTE = args.quote.upper()
    UNIVERSE_LIMIT = max(1, int(args.max))
    EX_IDS = resolve_exchanges(args.ex, args.ex_limit)
    # Exclude exchanges explicitly if requested
    if args.exclude_ex:
        try:
            excludes = {
                e.strip().lower() for e in args.exclude_ex.split(",") if e.strip()
            }
            EX_IDS = [e for e in EX_IDS if e not in excludes]
        except Exception:
            pass
    if args.ex_auth_only:
        ex_ids_auth = []
        for ex_id in EX_IDS:
            try:
                if creds_from_env(ex_id):
                    ex_ids_auth.append(ex_id)
            except Exception:
                pass
        if not ex_ids_auth:
            logger.warning(
                "--ex_auth_only: ninguna exchange con credenciales; nada que hacer"
            )
            return
        EX_IDS = ex_ids_auth

    # Determine allowed anchor quotes for BF cycles
    allowed_quotes: List[str] = []
    if args.bf_allowed_quotes:
        try:
            allowed_quotes = [
                q.strip().upper()
                for q in args.bf_allowed_quotes.split(",")
                if q.strip()
            ]
        except Exception:
            allowed_quotes = [QUOTE]
    else:
        allowed_quotes = [QUOTE]
    # If simulation from wallet is requested, ensure USDT and USDC are considered anchors
    if args.simulate_from_wallet:
        for q in ("USDT", "USDC"):
            if q not in allowed_quotes:
                allowed_quotes.append(q)

    # Determine if we should clear the console (allow overrides)
    env_no_clear = os.environ.get("ARBITRAJE_NO_CLEAR")
    do_console_clear = (
        bool(args.console_clear)
        and not bool(args.no_console_clear)
        and not bool(env_no_clear)
    )

    logger.info("Mode=%s | quote=%s | ex=%s", args.mode, QUOTE, ",".join(EX_IDS))

    swaps_blacklist_map: Dict[str, set[str]] = load_swaps_blacklist()

    # Pre-create and cache ccxt exchange instances (and markets) to speed up repeated iterations
    ex_instances: Dict[str, ccxt.Exchange] = {}
    try:
        preload_for_modes = {"bf", "tri"}
        do_preload = True
        try:
            do_preload = bool(getattr(args, "preload", True)) and not bool(
                getattr(args, "offline", False)
            )
        except Exception:
            do_preload = True
        if args.mode in preload_for_modes and do_preload:
            for _ex in EX_IDS:
                try:
                    inst = load_exchange_auth_if_available(
                        _ex, args.timeout, use_auth=bool(creds_from_env(_ex))
                    )
                    try:
                        # Preload and cache markets inside the instance
                        inst.load_markets()
                    except Exception:
                        pass
                    ex_instances[_ex] = inst
                except Exception:
                    continue
    except Exception:
        pass

    # ---------------------------
    # HEALTH MODE
    # ---------------------------
    if args.mode == "health":
        paths.LOGS_DIR.mkdir(parents=True, exist_ok=True)
        paths.OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
        # Clean previous logs to avoid mixing runs
        try:
            import shutil

            if paths.LOGS_DIR.exists():
                for p in paths.LOGS_DIR.iterdir():
                    try:
                        if p.is_file():
                            p.unlink(missing_ok=True)  # type: ignore[arg-type]
                        elif p.is_dir():
                            shutil.rmtree(p, ignore_errors=True)
                    except Exception:
                        continue
            paths.LOGS_DIR.mkdir(parents=True, exist_ok=True)
        except Exception:
            # Do not fail the run if cleanup fails
            pass
        health_file = paths.LOGS_DIR / "health.txt"
        rows = []
        for ex_id in EX_IDS:
            pub_ok = False
            markets_ok = False
            ticker_ok = False
            status_ok = None
            time_ok = None
            creds_present = False
            balance_ok = None
            nonzero_assets_count = None
            nonzero_assets_sample = []
            try:
                # Public checks
                ex_pub = load_exchange(ex_id, args.timeout)
                # quick time/status checks if supported
                if safe_has(ex_pub, "fetchTime"):
                    try:
                        _ = ex_pub.fetch_time()
                        time_ok = True
                    except Exception:
                        time_ok = False
                if safe_has(ex_pub, "fetchStatus"):
                    try:
                        st = ex_pub.fetch_status()
                        status_ok = True if st else True
                    except Exception:
                        status_ok = False
                # markets
                try:
                    markets = ex_pub.load_markets()
                    markets_ok = True
                    pub_ok = True
                    # try a common ticker
                    test_symbol = None
                    if "BTC/USDT" in markets:
                        test_symbol = "BTC/USDT"
                    else:
                        # pick first USDT market if any
                        for s, m in markets.items():
                            if m.get("quote") == "USDT":
                                test_symbol = s
                                break
                    if test_symbol and safe_has(ex_pub, "fetchTicker"):
                        try:
                            t = ex_pub.fetch_ticker(test_symbol)
                            if t and (t.get("bid") or t.get("last") or t.get("ask")):
                                ticker_ok = True
                        except Exception:
                            ticker_ok = False
                except Exception:
                    markets_ok = False
            except Exception:
                pub_ok = False

            # Credential presence and balance access
            try:
                c = creds_from_env(ex_id)
                creds_present = bool(c)
                if creds_present:
                    ex_auth = load_exchange_auth_if_available(
                        ex_id, args.timeout, use_auth=True
                    )
                    try:
                        bal = ex_auth.fetch_balance()
                        # count nonzero assets (total)
                        total = bal.get("total") or {}
                        nonzero = []
                        for k, v in total.items():
                            try:
                                if float(v) > 0:
                                    nonzero.append(k)
                            except Exception:
                                continue
                        nonzero_assets_count = len(nonzero)
                        nonzero_assets_sample = nonzero[:5]
                        balance_ok = True
                    except Exception:
                        balance_ok = False
            except Exception:
                pass

            extra_cols = {}
            # Optional direct Binance REST checks (only for binance)
            if ex_id == "binance" and creds_present:
                try:
                    api_key = os.environ.get("BINANCE_API_KEY")
                    api_secret = os.environ.get("BINANCE_API_SECRET")
                    # Convert pairs (market-data like)
                    pairs = binance_api.get_convert_pairs(
                        api_key, api_secret, timeout=args.timeout
                    )
                    extra_cols["convert_pairs_count"] = (
                        len(pairs) if isinstance(pairs, list) else None
                    )
                    # Persist to CSV
                    try:
                        if isinstance(pairs, list) and pairs:
                            df_pairs = pd.DataFrame(pairs)
                            df_pairs.to_csv(
                                paths.OUTPUTS_DIR / "binance_convert_pairs.csv",
                                index=False,
                            )
                    except Exception:
                        pass
                except Exception:
                    extra_cols["convert_pairs_count"] = None
                try:
                    # Convert asset info (USER_DATA signed)
                    asset_info = binance_api.get_convert_asset_info(
                        api_key, api_secret, timeout=args.timeout
                    )
                    extra_cols["asset_info_count"] = (
                        len(asset_info) if isinstance(asset_info, list) else None
                    )
                    # Persist to CSV
                    try:
                        if isinstance(asset_info, list) and asset_info:
                            df_assets = pd.DataFrame(asset_info)
                            df_assets.to_csv(
                                paths.OUTPUTS_DIR / "binance_convert_asset_info.csv",
                                index=False,
                            )
                    except Exception:
                        pass
                except Exception:
                    extra_cols["asset_info_count"] = None
            rows.append(
                {
                    "exchange": ex_id,
                    "public_ok": pub_ok,
                    "markets_ok": markets_ok,
                    "ticker_ok": ticker_ok,
                    "status_ok": status_ok,
                    "time_ok": time_ok,
                    "creds_present": creds_present,
                    "balance_ok": balance_ok,
                    "nonzero_assets_count": nonzero_assets_count,
                    "nonzero_assets_sample": (
                        ",".join(nonzero_assets_sample)
                        if nonzero_assets_sample
                        else None
                    ),
                    **extra_cols,
                }
            )

        # Log to console in a compact way
        headers = [
            "exchange",
            "public_ok",
            "markets_ok",
            "ticker_ok",
            "status_ok",
            "time_ok",
            "creds_present",
            "balance_ok",
            "nonzero_assets_count",
            "nonzero_assets_sample",
            "convert_pairs_count",
            "asset_info_count",
        ]
        df = pd.DataFrame(rows, columns=headers)
        logger.info(
            "\n%s", tabulate(df, headers="keys", tablefmt="github", showindex=False)
        )
        try:
            with open(health_file, "w", encoding="utf-8") as fh:
                fh.write(
                    tabulate(df, headers="keys", tablefmt="github", showindex=False)
                )
                fh.write("\n")
        except Exception:
            pass
        return

    # ---------------------------
    # BALANCE MODE (read-only)
    # ---------------------------
    if args.mode == "balance":
        results = []
        for ex_id in EX_IDS:
            try:
                # Only attempt if API keys exist in env
                env = os.environ
                creds = {}
                if ex_id == "binance":
                    k = env_get_stripped("BINANCE_API_KEY")
                    s = env_get_stripped("BINANCE_API_SECRET")
                    if not (k and s):
                        logger.info(
                            "%s: sin credenciales en env (BINANCE_API_KEY/SECRET)",
                            ex_id,
                        )
                        continue
                    # If native requested, use direct REST
                    if args.balance_provider == "native":
                        try:
                            acct = binance_api.get_account_balances(
                                k, s, timeout=args.timeout
                            )
                            balances = acct.get("balances") or []
                            nonzero = []
                            usdt_free = usdt_total = 0.0
                            usdc_free = usdc_total = 0.0
                            for b in balances:
                                try:
                                    free = float(b.get("free", 0) or 0)
                                    locked = float(b.get("locked", 0) or 0)
                                    total = free + locked
                                    if total > 0:
                                        nonzero.append((b.get("asset"), free, total))
                                    asset = str(b.get("asset") or "").upper()
                                    if asset == "USDT":
                                        usdt_free = free
                                        usdt_total = total
                                    elif asset == "USDC":
                                        usdc_free = free
                                        usdc_total = total
                                except Exception:
                                    continue
                            nonzero.sort(key=lambda x: x[2], reverse=True)
                            top = nonzero[:20]
                            logger.info(
                                "%s balance (native, top 20 non-zero): %s",
                                ex_id,
                                ", ".join(
                                    [f"{ccy}:{total}" for ccy, _free, total in top]
                                )
                                or "(vacío)",
                            )
                            logger.info(
                                "%s saldos (native): USDT free=%.8f total=%.8f | USDC free=%.8f total=%.8f",
                                ex_id,
                                usdt_free,
                                usdt_total,
                                usdc_free,
                                usdc_total,
                            )
                            results.append({"exchange": ex_id, "assets": top})
                            continue
                        except Exception as e:
                            logger.warning(
                                "%s: native balance falló: %s; fallback a ccxt",
                                ex_id,
                                e,
                            )
                    # If connector requested, use official Binance Spot SDK
                    if args.balance_provider == "connector":
                        try:
                            from binance_common.configuration import (
                                ConfigurationRestAPI as BConfigRest,
                            )
                            from binance_common.constants import (
                                SPOT_REST_API_PROD_URL as BSPOT_URL,
                            )
                            from binance_sdk_spot.spot import Spot as BSpot

                            api_key = k
                            api_secret = s
                            # Allow overriding base path (e.g., binance.us) via env
                            base_path = (
                                env_get_stripped("BINANCE_SPOT_BASE_PATH")
                                or env_get_stripped("BINANCE_API_BASE")
                                or BSPOT_URL
                            )
                            cfg = BConfigRest(
                                api_key=api_key,
                                api_secret=api_secret,
                                base_path=base_path,
                            )
                            client = BSpot(config_rest_api=cfg)
                            # omit_zero_balances=True to reduce payload
                            recv_window_env = env_get_stripped("BINANCE_RECV_WINDOW")
                            recv_window = None
                            try:
                                if recv_window_env:
                                    recv_window = float(recv_window_env)
                            except Exception:
                                recv_window = None
                            try:
                                resp = client.rest_api.get_account(
                                    omit_zero_balances=True, recv_window=recv_window
                                )
                            except Exception as e_call:
                                msg = str(e_call)
                                if "Too many parameters" in msg or "expected '" in msg:
                                    # Retry with minimal parameters (some regions may not accept additional args)
                                    resp = client.rest_api.get_account()
                                else:
                                    raise
                            data = resp.data()
                            assets = []
                            usdt_total = usdt_free = 0.0
                            usdc_total = usdc_free = 0.0
                            for bal in data.balances or []:
                                try:
                                    asset = bal.asset
                                    free = float(bal.free or 0)
                                    locked = float(bal.locked or 0)
                                    total = free + locked
                                    if total > 0:
                                        assets.append((asset, free, total))
                                    if str(asset).upper() == "USDT":
                                        usdt_total = total
                                        usdt_free = free
                                    if str(asset).upper() == "USDC":
                                        usdc_total = total
                                        usdc_free = free
                                except Exception:
                                    continue
                            assets.sort(key=lambda x: x[2], reverse=True)
                            top = assets[:20]
                            logger.info(
                                "%s balance (connector, top 20 non-zero): %s",
                                ex_id,
                                ", ".join(
                                    [f"{ccy}:{total}" for ccy, _free, total in top]
                                )
                                or "(vacío)",
                            )
                            logger.info(
                                "%s saldos (connector): USDT free=%.8f total=%.8f | USDC free=%.8f total=%.8f",
                                ex_id,
                                usdt_free,
                                usdt_total,
                                usdc_free,
                                usdc_total,
                            )
                            results.append(
                                {
                                    "exchange": ex_id,
                                    "assets": top,
                                    "USDT_free": usdt_free,
                                    "USDT_total": usdt_total,
                                }
                            )
                            continue
                        except Exception as e:
                            logger.warning(
                                "%s: connector balance falló: %s; fallback a ccxt",
                                ex_id,
                                e,
                            )
                    # Default ccxt path
                    creds = {"apiKey": k, "secret": s}
                elif ex_id == "bybit":
                    if not (env.get("BYBIT_API_KEY") and env.get("BYBIT_API_SECRET")):
                        logger.info(
                            "%s: sin credenciales en env (BYBIT_API_KEY/SECRET)", ex_id
                        )
                        continue
                    creds = {
                        "apiKey": env.get("BYBIT_API_KEY"),
                        "secret": env.get("BYBIT_API_SECRET"),
                    }
                elif ex_id == "bitget":
                    if not (
                        env.get("BITGET_API_KEY")
                        and env.get("BITGET_API_SECRET")
                        and env.get("BITGET_PASSWORD")
                    ):
                        logger.info(
                            "%s: sin credenciales en env (BITGET_API_KEY/SECRET/PASSWORD)",
                            ex_id,
                        )
                        continue
                    # Official Bitget SDK provider (optional)
                    if args.balance_provider == "bitget_sdk":
                        # If SDK isn't installed, silently fallback to ccxt (avoid noisy warnings)
                        try:
                            import importlib.util as _iutil  # type: ignore

                            if _iutil.find_spec("bitget") is None:
                                logger.info(
                                    "%s: bitget_sdk no instalado; usando ccxt", ex_id
                                )
                            else:
                                # Preferred env vars
                                bg_key = env_get_stripped("BITGET_API_KEY")
                                bg_secret = env_get_stripped("BITGET_API_SECRET")
                                bg_pass = env_get_stripped("BITGET_PASSWORD")
                                # Try SDK import pattern 1
                                from bitget.openapi import Spot as BGSpot  # type: ignore

                                client = BGSpot(
                                    api_key=bg_key,
                                    secret_key=bg_secret,
                                    passphrase=bg_pass,
                                )
                                # Attempt a common account/balance call
                                # Depending on SDK version, method names differ; try a few options
                                data = None
                                for fn in (
                                    "assets",
                                    "account_assets",
                                    "get_account_assets",
                                ):
                                    if hasattr(client, fn):
                                        try:
                                            resp = getattr(client, fn)()
                                            data = (
                                                resp.get("data")
                                                if isinstance(resp, dict)
                                                else resp
                                            )
                                            break
                                        except Exception:
                                            continue
                                if data is None:
                                    raise RuntimeError(
                                        "Bitget SDK: no se pudo obtener assets (método no encontrado)"
                                    )
                                usdt_free = usdt_total = 0.0
                                usdc_free = usdc_total = 0.0
                                assets = []
                                # Normalize list of balances
                                for item in data or []:
                                    try:
                                        ccy = str(
                                            item.get("coin")
                                            or item.get("asset")
                                            or item.get("currency")
                                            or ""
                                        ).upper()
                                        avail = float(
                                            item.get("available")
                                            or item.get("availableQty")
                                            or item.get("free")
                                            or 0.0
                                        )
                                        frozen = float(
                                            item.get("frozen")
                                            or item.get("locked")
                                            or 0.0
                                        )
                                        total = float(
                                            item.get("total") or (avail + frozen)
                                        )
                                        if total > 0:
                                            assets.append((ccy, avail, total))
                                        if ccy == "USDT":
                                            usdt_free, usdt_total = avail, total
                                        elif ccy == "USDC":
                                            usdc_free, usdc_total = avail, total
                                    except Exception:
                                        continue
                                assets.sort(key=lambda x: x[2], reverse=True)
                                top = assets[:20]
                                logger.info(
                                    "%s balance (bitget_sdk, top 20 non-zero): %s",
                                    ex_id,
                                    ", ".join(
                                        [f"{ccy}:{total}" for ccy, _free, total in top]
                                    )
                                    or "(vacío)",
                                )
                                logger.info(
                                    "%s saldos (bitget_sdk): USDT free=%.8f total=%.8f | USDC free=%.8f total=%.8f",
                                    ex_id,
                                    usdt_free,
                                    usdt_total,
                                    usdc_free,
                                    usdc_total,
                                )
                                results.append(
                                    {
                                        "exchange": ex_id,
                                        "assets": top,
                                        "USDT_free": usdt_free,
                                        "USDT_total": usdt_total,
                                    }
                                )
                                continue
                        except Exception as e_sdk:
                            # Downgrade to info and fallback quietly
                            logger.info(
                                "%s: bitget_sdk falló (%s); usando ccxt", ex_id, e_sdk
                            )
                    # Default ccxt path for Bitget
                    creds = {
                        "apiKey": env.get("BITGET_API_KEY"),
                        "secret": env.get("BITGET_API_SECRET"),
                        "password": env.get("BITGET_PASSWORD"),
                    }
                elif ex_id == "coinbase":
                    # Coinbase Advanced requires apiKey/secret/password in ccxt
                    if not (
                        env.get("COINBASE_API_KEY")
                        and env.get("COINBASE_API_SECRET")
                        and env.get("COINBASE_API_PASSWORD")
                    ):
                        logger.info(
                            "%s: sin credenciales en env (COINBASE_API_KEY/SECRET/PASSWORD)",
                            ex_id,
                        )
                        continue
                    creds = {
                        "apiKey": env.get("COINBASE_API_KEY"),
                        "secret": env.get("COINBASE_API_SECRET"),
                        "password": env.get("COINBASE_API_PASSWORD"),
                    }
                else:
                    # Generic path for any other exchange supported by ccxt, if env creds exist
                    creds = creds_from_env(ex_id)
                    if not creds:
                        logger.info("%s: sin credenciales en env (omitido)", ex_id)
                        continue
                cls = getattr(ccxt, ex_id)
                ex = cls({"enableRateLimit": True, **creds})
                bal = ex.fetch_balance()
                # summarize non-zero balances (free or total)
                nonzero = []
                usdt_free = usdt_total = 0.0
                usdc_free = usdc_total = 0.0
                for ccy, b in (bal.get("total") or {}).items():
                    try:
                        amt_total = float(b)
                        amt_free = float((bal.get("free") or {}).get(ccy, 0.0))
                        ccy_up = str(ccy).upper()
                        if amt_total > 0:
                            nonzero.append((ccy, amt_free, amt_total))
                        if ccy_up == "USDT":
                            usdt_free = amt_free
                            usdt_total = amt_total
                        elif ccy_up == "USDC":
                            usdc_free = amt_free
                            usdc_total = amt_total
                    except Exception:
                        continue
                nonzero.sort(key=lambda x: x[2], reverse=True)
                top = nonzero[:20]
                logger.info(
                    "%s balance (top 20 non-zero): %s",
                    ex_id,
                    ", ".join([f"{ccy}:{total}" for ccy, _free, total in top])
                    or "(vacío)",
                )
                logger.info(
                    "%s saldos (ccxt): USDT free=%.8f total=%.8f | USDC free=%.8f total=%.8f",
                    ex_id,
                    usdt_free,
                    usdt_total,
                    usdc_free,
                    usdc_total,
                )
                results.append({"exchange": ex_id, "assets": top})
            except Exception as e:
                logger.warning("%s: fetch_balance falló: %s", ex_id, e)
        return

    # ---------------
    # TRIANGULAR MODE
    # ---------------
    if args.mode == "tri":
        results: List[dict] = []
        paths.OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
        tri_csv = paths.OUTPUTS_DIR / f"arbitrage_tri_{QUOTE.lower()}_ccxt.csv"
        current_file = paths.LOGS_DIR / "current_tri.txt"
        tri_iter_csv = (
            paths.OUTPUTS_DIR / f"arbitrage_tri_current_{QUOTE.lower()}_ccxt.csv"
        )
        # iteration watchdog for TRI mode (configured via YAML)
        iteration_watchdog_sec = float(
            getattr(args, "iteration_watchdog_sec", 0.0) or 0.0
        )
        _prev_iter_ts = None
        for it in range(1, int(max(1, args.repeat)) + 1):
            _now = time.time()
            if _prev_iter_ts is not None and iteration_watchdog_sec > 0:
                _delta = _now - _prev_iter_ts
                if _delta > iteration_watchdog_sec:
                    logger.error(
                        "Iteration watchdog triggered (tri): previous iteration "
                        "start delta=%.2fs > configured %.2fs; exiting",
                        _delta,
                        iteration_watchdog_sec,
                    )
                    print(
                        f"Iteration watchdog (tri): delayed by {_delta:.2f}s "
                        f"(limit {iteration_watchdog_sec}s). Exiting."
                    )
                    break
            _prev_iter_ts = _now
            ts = pd.Timestamp.utcnow().isoformat()
            swaps_blacklist_map = load_swaps_blacklist()
            # Prefetch wallet balances once per iteration for simulation rendering
            wallet_buckets_cache: Dict[str, Dict[str, float]] = {}
            try:
                if args.simulate_compound and getattr(
                    args, "simulate_from_wallet", False
                ):
                    wallet_buckets_cache = _prefetch_wallet_buckets(list(EX_IDS), args)
            except Exception:
                wallet_buckets_cache = {}
            # Hydrate simulation balances from wallet snapshot once (first iteration) if requested
            try:
                if (
                    args.simulate_compound
                    and getattr(args, "simulate_from_wallet", False)
                    and it == 1
                    and wallet_buckets_cache
                ):
                    for ex_id in EX_IDS:
                        st = sim_state.get(ex_id)
                        if not st:
                            continue
                        wb = wallet_buckets_cache.get(ex_id) or {}
                        usdt = float(wb.get("USDT", 0.0) or 0.0)
                        usdc = float(wb.get("USDC", 0.0) or 0.0)
                        prefer = str(
                            getattr(args, "simulate_prefer", "auto") or "auto"
                        ).upper()
                        chosen_ccy = st.get("ccy") or "USDT"
                        chosen_bal = 0.0
                        if prefer == "USDT":
                            chosen_ccy, chosen_bal = "USDT", usdt
                        elif prefer == "USDC":
                            chosen_ccy, chosen_bal = "USDC", usdc
                        else:
                            if usdt >= usdc and usdt > 0:
                                chosen_ccy, chosen_bal = "USDT", usdt
                            elif usdc > 0:
                                chosen_ccy, chosen_bal = "USDC", usdc
                            else:
                                chosen_ccy, chosen_bal = (st.get("ccy") or "USDT"), 0.0
                        sim_state[ex_id] = {
                            "ccy": chosen_ccy,
                            "balance": float(chosen_bal),
                            "start_balance": float(chosen_bal),
                            "start_ccy": chosen_ccy,
                        }
            except Exception:
                pass
            if do_console_clear:
                try:
                    if os.name == "nt":
                        os.system("cls")
                    else:
                        print("\033[2J\033[H", end="")
                except Exception:
                    pass
            # Clean per-iteration artifacts
            try:
                if current_file.exists():
                    current_file.unlink()  # type: ignore[arg-type]
            except Exception:
                pass
            try:
                if tri_iter_csv.exists():
                    tri_iter_csv.unlink()  # type: ignore[arg-type]
            except Exception:
                pass
            try:
                tri_hist = paths.LOGS_DIR / "tri_history.txt"
                if tri_hist.exists():
                    tri_hist.unlink()  # type: ignore[arg-type]
            except Exception:
                pass
            iter_lines: List[str] = []
            iter_results: List[dict] = []
            for ex_id in EX_IDS:
                try:
                    ex = load_exchange(ex_id, args.timeout)
                    if not safe_has(ex, "fetchTickers"):
                        if ex_id != "bitso":
                            logger.warning(
                                "%s: omitido (no soporta fetchTickers para tri)", ex_id
                            )
                        continue
                    markets = ex.load_markets()
                    tickers = ex.fetch_tickers()
                    ex_norm = normalize_ccxt_id(ex_id)
                    exchange_blacklist = swaps_blacklist_map.get(ex_norm, set())
                    tokens = set()
                    for s, m in markets.items():
                        if not m.get("active", True):
                            continue
                        base = str(m.get("base") or "").upper()
                        quote = str(m.get("quote") or "").upper()
                        if base and quote and (base == QUOTE or quote == QUOTE):
                            other = quote if base == QUOTE else base
                            if other:
                                tokens.add(str(other).upper())
                    tokens = [t for t in list(tokens) if isinstance(t, str)]
                    if exchange_blacklist:
                        tokens = [
                            t
                            for t in tokens
                            if not _pair_is_blacklisted(exchange_blacklist, QUOTE, t)
                        ]
                    tokens = tokens[: args.tri_currencies_limit]
                    fee = float(args.tri_fee)
                    opps: List[dict] = []
                    for i in range(len(tokens)):
                        X = tokens[i]
                        if _pair_is_blacklisted(exchange_blacklist, QUOTE, X):
                            continue
                        for j in range(len(tokens)):
                            if j == i:
                                continue
                            Y = tokens[j]
                            if _pair_is_blacklisted(exchange_blacklist, X, Y):
                                continue
                            r1, qv1 = get_rate_and_qvol(
                                QUOTE, X, tickers, fee, args.tri_require_topofbook
                            )
                            if not r1:
                                continue
                            if args.tri_min_quote_vol > 0 and (
                                qv1 is None or qv1 < args.tri_min_quote_vol
                            ):
                                continue
                            r2, qv2 = get_rate_and_qvol(
                                X, Y, tickers, fee, args.tri_require_topofbook
                            )
                            if not r2:
                                continue
                            if args.tri_min_quote_vol > 0 and (
                                qv2 is None or qv2 < args.tri_min_quote_vol
                            ):
                                continue
                            if _pair_is_blacklisted(exchange_blacklist, Y, QUOTE):
                                continue
                            r3, qv3 = get_rate_and_qvol(
                                Y, QUOTE, tickers, fee, args.tri_require_topofbook
                            )
                            if not r3:
                                continue
                            if args.tri_min_quote_vol > 0 and (
                                qv3 is None or qv3 < args.tri_min_quote_vol
                            ):
                                continue
                            product = r1 * r2 * r3
                            net_pct = (product - 1.0) * 100.0
                            if net_pct >= args.tri_min_net:
                                inv_amt = float(args.inv)
                                est_after = round(inv_amt * product, 4)
                                opps.append(
                                    {
                                        "exchange": ex_id,
                                        "path": f"{QUOTE}->{X}->{Y}->{QUOTE}",
                                        "r1": round(r1, 8),
                                        "r2": round(r2, 8),
                                        "r3": round(r3, 8),
                                        "net_pct": round(net_pct, 4),
                                        "inv": inv_amt,
                                        "est_after": est_after,
                                        "iteration": it,
                                        "ts": ts,
                                    }
                                )
                    if opps:
                        opps.sort(key=lambda o: o["net_pct"], reverse=True)
                        lines = []
                        for o in opps[: args.tri_top]:
                            line = (
                                f"TRI@{o['exchange']} {o['path']} => net {o['net_pct']:.3f}% | "
                                f"{QUOTE} {o['inv']} -> {o['est_after']}"
                            )
                            lines.append(line)
                            iter_lines.append(line)
                        logger.info("== TRIANGULAR @ %s ==", ex_id)
                        logger.info("Encontradas: %d", len(opps))
                        logger.info("\n" + "\n".join(lines))
                        results.extend(opps)
                        iter_results.extend(opps)
                except Exception as e:
                    logger.warning("%s: triangular scan falló: %s", ex_id, e)
            # Write current-only file and per-iteration CSV
            try:
                try:
                    if iter_results:
                        pd.DataFrame(iter_results).to_csv(tri_iter_csv, index=False)
                    else:
                        pd.DataFrame(
                            columns=[
                                "exchange",
                                "path",
                                "r1",
                                "r2",
                                "r3",
                                "net_pct",
                                "inv",
                                "est_after",
                                "iteration",
                                "ts",
                            ]
                        ).to_csv(tri_iter_csv, index=False)
                except Exception:
                    pass
                with open(current_file, "w", encoding="utf-8") as fh:
                    fh.write(f"[TRI] Iteración {it}/{args.repeat} @ {ts}\n")
                    if iter_lines:
                        fh.write("\n".join(iter_lines) + "\n")
                    else:
                        fh.write("(sin oportunidades en esta iteración)\n")
                tri_hist = paths.LOGS_DIR / "tri_history.txt"
                with open(tri_hist, "w", encoding="utf-8") as fh:
                    fh.write(f"[TRI] Iteración {it}/{args.repeat} @ {ts}\n")
                    if iter_lines:
                        fh.write("\n".join(iter_lines) + "\n\n")
                    else:
                        fh.write("(sin oportunidades en esta iteración)\n\n")
            except Exception:
                pass
            if it < args.repeat:
                time.sleep(max(0.0, args.repeat_sleep))
            # Save CSV and exit tri mode
            if results:
                pd.DataFrame(results).to_csv(tri_csv, index=False)
            else:
                pd.DataFrame(
                    columns=[
                        "exchange",
                        "path",
                        "r1",
                        "r2",
                        "r3",
                        "net_pct",
                        "inv",
                        "est_after",
                        "iteration",
                        "ts",
                    ]
                ).to_csv(tri_csv, index=False)
            logger.info("TRI CSV: %s", tri_csv)
            return

    # -----------
    # BF MODE
    # -----------
    if args.mode == "bf":
        logger.info("[TIMING] BF main loop: starting full run")
        logger.info("[DEBUG] EX_IDS justo antes del ciclo: %s", EX_IDS)
        t_bf_main_start = time.time()
        results_bf: List[dict] = []
        # Persistence map: (exchange, path) -> stats
        persistence: Dict[Tuple[str, str], Dict[str, object]] = {}
        paths.OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
        bf_csv = paths.OUTPUTS_DIR / f"arbitrage_bf_{QUOTE.lower()}_ccxt.csv"
        bf_persist_csv = (
            paths.OUTPUTS_DIR / f"arbitrage_bf_{QUOTE.lower()}_persistence.csv"
        )
        bf_sim_csv = (
            paths.OUTPUTS_DIR / f"arbitrage_bf_simulation_{QUOTE.lower()}_ccxt.csv"
        )
        # Use lowercase snapshot filename consistently with repo conventions
        current_file = paths.LOGS_DIR / "current_bf.txt"
        # Optional per-iteration top-k persistence CSV
        bf_top_hist_csv = (
            paths.OUTPUTS_DIR / f"arbitrage_bf_top_{QUOTE.lower()}_history.csv"
        )
        # Per-iteration snapshot CSV (overwritten each iteration)
        bf_iter_csv = (
            paths.OUTPUTS_DIR / f"arbitrage_bf_current_{QUOTE.lower()}_ccxt.csv"
        )

        # Ensure BF snapshot log is clean at the start of every run to avoid mixing sessions
        try:
            import shutil

            paths.LOGS_DIR.mkdir(parents=True, exist_ok=True)
            # Keep bf_history.txt for accumulation; only reset current snapshot (clean legacy and canonical)
            for fname in ("current_bf.txt", "CURRENT_BF.txt"):
                fp = paths.LOGS_DIR / fname
                if fp.exists():
                    try:
                        if fp.is_file():
                            fp.unlink()  # type: ignore[arg-type]
                        else:
                            shutil.rmtree(fp, ignore_errors=True)
                    except Exception:
                        # Non-fatal if we can't delete; we will append later
                        pass
            # Optionally reset accumulated history files at start
            if args.bf_reset_history:
                for fname in ("bf_history.txt", "history_bf.txt", "HISTORY_BF.txt"):
                    fp = paths.LOGS_DIR / fname
                    try:
                        if fp.exists():
                            if fp.is_file():
                                fp.unlink()  # type: ignore[arg-type]
                            else:
                                shutil.rmtree(fp, ignore_errors=True)
                    except Exception:
                        pass
        except Exception:
            pass

    # Initialize simulation state (per exchange)
    sim_rows: List[dict] = []
    # reuse global sim_state dict (clear previous contents)
    sim_state.clear()
    if args.simulate_compound:
        for ex_id in EX_IDS:
            # Default anchor choice
            default_ccy = allowed_quotes[0] if allowed_quotes else QUOTE
            ccy = default_ccy
            bal_val: float = 0.0
            if args.simulate_from_wallet:
                # Do not fetch balances here to avoid slow startup; will hydrate at iteration start from cached wallet
                prefer = args.simulate_prefer
                if prefer == "USDT":
                    ccy = "USDT"
                elif prefer == "USDC":
                    ccy = "USDC"
                else:
                    # auto: keep default; will switch based on wallet snapshot
                    ccy = ccy
                bal_val = 0.0
            else:
                # Non-wallet simulation can start from provided value or inv
                bal_val = (
                    float(args.simulate_start)
                    if args.simulate_start is not None
                    else float(args.inv)
                )
            # Track starting state to summarize PnL at the end
            sim_state[ex_id] = {
                "ccy": ccy,
                "balance": float(bal_val),
                "start_balance": float(bal_val),
                "start_ccy": ccy,
            }

    # Cache of wallet balances per exchange for simulation/header rendering
    wallet_buckets_cache: Dict[str, Dict[str, float]] = {}

    # Ensure a visible BF snapshot stub exists from the start of the run (rest of content written per iteration)
    try:
        with open(current_file, "w", encoding="utf-8") as fh:
            ts0 = pd.Timestamp.utcnow().isoformat()
            fh.write(f"[BF] Inicio @ {ts0}\n\n")
        _sync_snapshot_alias()
    except Exception:
        pass

    # Cache adjacency per exchange for current process to avoid recomputing each iteration
    _adjacency_cache: Dict[str, Dict[str, set]] = {}
    # Micro-cache: currencies universe per exchange when qvol ranking is OFF
    # Keyed by (ex_id, limit, dual_quote_flag, anchors_signature)
    _currencies_cache: Dict[tuple, List[str]] = {}
    # Anchors are static within a run; compute once
    anchors_static: set[str] = (
        set([q for q in allowed_quotes]) if allowed_quotes else {QUOTE}
    )

    # Note: _sync_snapshot_alias is provided at module level for linter/namespace stability.
    # The original implementation copied current_bf.txt to CURRENT_BF.txt; the module-level
    # stub will be used in headless runs where filesystem mirroring isn't required.

    def bf_worker(ex_id: str, it: int, ts: str) -> Tuple[str, List[str], List[dict]]:
        local_lines: List[str] = []
        local_results: List[dict] = []
        t0_total = time.time()
        logger.info(f"[TIMING] bf_worker({ex_id}) start")
        t_load_ex_start = time.time()
        # In offline mode avoid creating exchange instances and network calls
        if getattr(args, "offline", False):
            ex = ex_instances.get(ex_id) or None
        else:
            ex = ex_instances.get(ex_id) or load_exchange_auth_if_available(
                ex_id, args.timeout, use_auth=bool(creds_from_env(ex_id))
            )
        # Force authenticated instance regardless of CLI/YAML
        if not getattr(ex, "apiKey", None):
            ex = load_exchange_auth_if_available(ex_id, args.timeout, use_auth=True)
        t_load_ex_end = time.time()
        try:
            logger.info(
                f"[TIMING] bf_worker({ex_id}): load_exchange {t_load_ex_end-t_load_ex_start:.3f}s"
            )
        except Exception:
            # If start var missing for any reason, log basic duration
            logger.info(
                f"[TIMING] bf_worker({ex_id}): load_exchange took {t_load_ex_end-t0_total:.3f}s (fallback)"
            )
        if not safe_has(ex, "fetchTickers"):
            # Silence noisy warning for exchanges like bitso that don't support fetchTickers for BF
            if ex_id != "bitso":
                logger.warning("%s: omitido (no soporta fetchTickers para BF)", ex_id)
            return ex_id, local_lines, local_results
        t0_markets = time.time()
        markets = None
        if getattr(args, "offline", False):
            # Try load markets from offline snapshot if available; else skip network
            if offline_snapshot_map and isinstance(offline_snapshot_map, dict):
                markets = offline_snapshot_map.get(ex_id, {}).get("markets")
        if markets is None:
            # Online path: prefer cached ex.markets; else load
            markets = getattr(ex, "markets", None)
            try:
                if not markets:
                    markets = ex.load_markets()
            except Exception:
                markets = {}
        if not isinstance(markets, dict):
            markets = {}
        t1_markets = time.time()
        logger.info(
            f"[TIMING] bf_worker({ex_id}): load_markets {t1_markets-t0_markets:.3f}s"
        )
        t0_adj = time.time()
        adjacency = _adjacency_cache.get(ex_id)
        if adjacency is None:
            adjacency = _build_adjacency_from_markets(markets)
            _adjacency_cache[ex_id] = adjacency
        t1_adj = time.time()
        logger.info(
            f"[TIMING] bf_worker({ex_id}): build_adjacency {t1_adj-t0_adj:.3f}s"
        )
        t0_currency = time.time()
        ex_norm = normalize_ccxt_id(ex_id)
        exchange_blacklist = swaps_blacklist_map.get(ex_norm, set())
        if args.bf_debug and exchange_blacklist:
            logger.info(
                "[BF-DBG] %s blacklist_pairs=%d", ex_id, len(exchange_blacklist)
            )
        t1_currency = time.time()
        logger.info(
            f"[TIMING] bf_worker({ex_id}): currency_selection {t1_currency-t0_currency:.3f}s"
        )
        # Apply per-exchange overrides (best-effort)
        bf_min_net = float(
            _apply_exchange_override("bf_", ex_id, "min_net", args.bf_min_net)
        )
        bf_fee = float(_apply_exchange_override("bf_", ex_id, "fee", args.bf_fee))
        bf_depth_levels = int(
            _apply_exchange_override(
                "bf_", ex_id, "depth_levels", getattr(args, "bf_depth_levels", 0)
            )
        )
        bf_latency_penalty_bps = float(
            _apply_exchange_override(
                "bf_",
                ex_id,
                "latency_penalty_bps",
                getattr(args, "bf_latency_penalty_bps", 0.0),
            )
        )
        bf_min_quote_vol = float(
            _apply_exchange_override(
                "bf_", ex_id, "min_quote_vol", args.bf_min_quote_vol
            )
        )
        bf_require_topofbook = bool(
            _apply_exchange_override(
                "bf_", ex_id, "require_topofbook", args.bf_require_topofbook
            )
        )
        bf_top = int(_apply_exchange_override("bf_", ex_id, "top", args.bf_top))
        bf_currencies_limit = int(
            _apply_exchange_override(
                "bf_", ex_id, "currencies_limit", args.bf_currencies_limit
            )
        )
        bf_revalidate_depth = bool(
            _apply_exchange_override(
                "bf_", ex_id, "revalidate_depth", args.bf_revalidate_depth
            )
        )
        bf_use_ws = bool(
            _apply_exchange_override("bf_", ex_id, "use_ws", args.bf_use_ws)
        )
        # Determine investment amount possibly constrained by balance
        inv_amt_cfg = float(args.inv)
        inv_amt_effective = inv_amt_cfg
        # Always use wallet balance for effective investment; if inv==0, use full wallet
        bal = fetch_quote_balance(ex, QUOTE, kind="free")
        if bal is not None:
            bal_f = max(0.0, float(bal))
            if inv_amt_cfg <= 0.0:
                inv_amt_effective = bal_f
            else:
                inv_amt_effective = max(0.0, min(inv_amt_cfg, bal_f))
        else:
            # Balance unavailable: fall back to config inv (may be 0)
            inv_amt_effective = max(0.0, inv_amt_cfg)
        # Build currency universe around allowed anchors (e.g., USDT and USDC)
        anchors = anchors_static
        currencies: List[str] | None = None
        # Reuse cached currencies when ranking is OFF to avoid recomputation
        if not args.bf_rank_by_qvol:
            cache_key = (
                ex_id,
                int(bf_currencies_limit),
                bool(args.bf_require_dual_quote),
                tuple(sorted(list(anchors))),
            )
            currencies = _currencies_cache.get(cache_key)
            if currencies and args.bf_debug:
                logger.info(
                    "[BF-DBG] %s currencies cache HIT: n=%d", ex_id, len(currencies)
                )
        if not currencies:
            tokens = set([q for q in anchors])
            # Build a map base -> set(quotes) to support dual-quote filtering
            base_to_quotes: Dict[str, set] = {}
            for s, m in markets.items():
                if not m.get("active", True):
                    continue
                base = m.get("base")
                quote = m.get("quote")
                if base and quote and (base in anchors or quote in anchors):
                    tokens.add(base)
                    tokens.add(quote)
                if base and quote:
                    b = str(base).upper()
                    q = str(quote).upper()
                    base_to_quotes.setdefault(b, set()).add(q)
            # If requested and we have 2+ anchors, restrict tokens to bases that have all anchors as quotes
            if args.bf_require_dual_quote and len(anchors) >= 2:
                required = set(anchors)
                filtered_tokens = set()
                for b, qs in base_to_quotes.items():
                    if required.issubset(qs):
                        filtered_tokens.add(b)
                # Keep anchors themselves too
                tokens = filtered_tokens | anchors
            currencies = [c for c in tokens if isinstance(c, str)]
            # If ranking is OFF, finalize list (limit + anchor-first) and cache it
            if not args.bf_rank_by_qvol:
                currencies = currencies[: max(1, bf_currencies_limit)]
                for q in allowed_quotes:
                    if q in currencies:
                        currencies = [q] + [c for c in currencies if c != q]
                        break
                _currencies_cache[cache_key] = list(currencies)
                if args.bf_debug:
                    logger.info(
                        "[BF-DBG] %s currencies cache SET: n=%d",
                        ex_id,
                        len(currencies),
                    )
        # Decide tickers mapping in a single place to avoid accidental overwrites.
        # Order of precedence:
        # 1) offline snapshot (if offline and snapshot map provided)
        # 2) qvol ranking path: batch fetch all tickers and compute qvol
        # 3) leave as empty mapping (techniques may use tokens only)
        t0_tickers = time.time()
        tickers = {}
        batch_supported = safe_has(ex, "fetchTickers")
        if getattr(args, "offline", False) and offline_snapshot_map:
            tickers = offline_snapshot_map.get(ex_id, {}).get("tickers", {}) or {}
        elif (
            (not getattr(args, "offline", False))
            and args.bf_rank_by_qvol
            and markets
            and batch_supported
        ):
            # Batch fetch tickers to compute per-currency quote volume and rank currencies
            try:
                tickers = ex.fetch_tickers() or {}
            except Exception:
                logger.exception(
                    "Failed to fetch tickers for qvol ranking for %s", ex_id
                )
                tickers = {}
            qvol_by_ccy: Dict[str, float] = {}
            for sym, t in (tickers or {}).items():
                try:
                    m = markets.get(sym) or {}
                    base = str(m.get("base") or "").upper()
                    quote = str(m.get("quote") or "").upper()
                    qv = get_quote_volume(t) or 0.0
                    if base:
                        qvol_by_ccy[base] = qvol_by_ccy.get(base, 0.0) + float(qv)
                    if quote:
                        qvol_by_ccy[quote] = qvol_by_ccy.get(quote, 0.0) + float(qv)
                except Exception:
                    continue
            currencies = sorted(
                currencies, key=lambda c: qvol_by_ccy.get(c, 0.0), reverse=True
            )
        elif (
            # Non-ranking path: still fetch tickers so techniques can build graphs
            (not getattr(args, "offline", False))
            and markets
            and batch_supported
        ):
            try:
                tickers = ex.fetch_tickers() or {}
                if args.bf_debug:
                    logger.info(
                        "[BF-DBG] %s rank_by_qvol disabled -> fetched %d tickers for graph",
                        ex_id,
                        len(tickers) if isinstance(tickers, dict) else 0,
                    )
            except Exception:
                logger.debug("fetch_tickers (non-ranking) failed for %s", ex_id)
                tickers = {}
        # Defensive: ensure tickers is a mapping
        if tickers is None or not isinstance(tickers, dict):
            tickers = {}
        # If ranking path was taken, apply limit and ensure anchor-first
        if args.bf_rank_by_qvol:
            currencies = currencies[: max(1, bf_currencies_limit)]
            for q in allowed_quotes:
                if q in currencies:
                    currencies = [q] + [c for c in currencies if c != q]
                    break
        t1_tickers = time.time()
        logger.info(
            f"[TIMING] bf_worker({ex_id}): fetch_tickers {t1_tickers-t0_tickers:.3f}s"
        )
        if args.bf_debug:
            try:
                logger.info(
                    "[BF-DBG] %s currencies=%d (anchors=%s)",
                    ex_id,
                    len(currencies),
                    ",".join(sorted(anchors)),
                )
            except Exception:
                logger.info("[BF-DBG] %s currencies=%d", ex_id, len(currencies))
        # Try delegating BF scan to engine_techniques if enabled. If delegation returns
        # results, we use them and skip the heavy in-process BF inner loop.
        # Prefer running BF in the techniques process pool unless explicitly disabled
        t0_delegate = time.time()

        # Optional debug path: reuse the optimized triangular worker to emit paths
        # even when BF finds no cycles (includes negative nets). Controlled by
        # --bf_debug_list_triangles or YAML bf.debug_list_triangles.
        try:
            if bool(getattr(args, "bf_debug_list_triangles", False)):
                # Temporarily relax TRI thresholds to surface many cycles (including negatives)
                _orig_tri_min_net = getattr(args, "tri_min_net", 0.5)
                _orig_tri_min_qv = getattr(args, "tri_min_quote_vol", 0.0)
                _orig_tri_limit = getattr(args, "tri_currencies_limit", 35)
                try:
                    setattr(args, "tri_min_net", -10000.0)
                    setattr(args, "tri_min_quote_vol", 0.0)
                    # widen token set a bit for discovery but keep bounded
                    setattr(
                        args,
                        "tri_currencies_limit",
                        max(int(_orig_tri_limit or 35), 60),
                    )
                except Exception:
                    pass
                _ex_id_tri, _lines_tri, _tri_res = tri_worker(ex_id, it, ts)
                # Restore original TRI args
                try:
                    setattr(args, "tri_min_net", _orig_tri_min_net)
                    setattr(args, "tri_min_quote_vol", _orig_tri_min_qv)
                    setattr(args, "tri_currencies_limit", _orig_tri_limit)
                except Exception:
                    pass
                # Map tri records into BF schema
                for rec in _tri_res or []:
                    try:
                        if "cycle" in rec and rec.get("net_bps_est") is not None:
                            path = rec.get("cycle")
                            net_pct = float(rec.get("net_bps_est", 0.0)) / 100.0
                            hops = max(0, str(path).count("->"))
                            inv_amt = float(inv_amt_effective)
                            est_after = (
                                round(inv_amt * (1.0 + net_pct / 100.0), 6)
                                if inv_amt is not None
                                else None
                            )
                            local_results.append(
                                {
                                    "exchange": ex_id,
                                    "path": path,
                                    "net_pct": round(net_pct, 4),
                                    "inv": inv_amt,
                                    "est_after": est_after,
                                    "hops": hops,
                                    "iteration": it,
                                    "ts": ts,
                                    "source": "tri",
                                }
                            )
                    except Exception:
                        continue
                # If we populated any results from triangles, return early for this exchange
                if local_results:
                    t_delegate_total = time.time()
                    logger.info(
                        f"[TIMING] bf_worker({ex_id}): total {t_delegate_total-t0_total:.3f}s (tri-debug)"
                    )
                    return ex_id, local_lines, local_results
        except Exception:
            # Non-fatal: continue with normal BF flow
            pass

        # If triangle debug is on and we already produced results, skip heavy techniques
        if bool(getattr(args, "bf_debug_list_triangles", False)) and local_results:
            t_delegate_total = time.time()
            logger.info(
                f"[TIMING] bf_worker({ex_id}): total {t_delegate_total-t0_total:.3f}s (tri-only short-circuit)"
            )
            return ex_id, local_lines, local_results

        if not getattr(args, "no_techniques_bf", False):
            try:
                from .engine_techniques import scan_arbitrage as _scan_arbitrage

                # Instrumentation: log tickers size and a small sample immediately
                # before assembling the payload to help debug zero-ticker cases.
                try:
                    tk_len = (
                        0
                        if tickers is None
                        else (len(tickers) if isinstance(tickers, dict) else 0)
                    )
                    sample_keys = []
                    if isinstance(tickers, dict):
                        sample_keys = list(tickers.keys())[:10]
                    logger.info(
                        "[BF-INST] ex=%s tickers_len=%d sample_keys=%s",
                        ex_id,
                        tk_len,
                        sample_keys,
                    )
                except Exception:
                    logger.exception("Failed to log BF instrumentation")

                payload = {
                    "ex_id": ex_id,
                    "ts": pd.Timestamp.utcnow().isoformat(),
                    "quote": QUOTE,
                    "tokens": currencies,
                    "tickers": tickers,
                    "fee": bf_fee,
                    "min_net": bf_min_net,
                    "top": bf_top,
                    "min_hops": getattr(args, "bf_min_hops", 0),
                    "max_hops": getattr(args, "bf_max_hops", 0),
                    "min_net_per_hop": getattr(args, "bf_min_net_per_hop", 0.0),
                    "min_quote_vol": bf_min_quote_vol,
                    "latency_penalty": bf_latency_penalty_bps,
                    "blacklist": list(exchange_blacklist),
                }
                # Pass through techniques config from YAML (if present) so
                # engine_techniques can pick up telemetry_file, inline settings, etc.
                techniques_cfg = {}
                try:
                    techniques_cfg = cfg_raw.get("techniques", {}) if cfg_raw else {}
                except Exception:
                    techniques_cfg = {}
                # allow CLI overrides for enabled/max_workers/rerank
                techniques_cfg.setdefault(
                    "enabled", getattr(args, "techniques_enabled", ["bellman_ford"])
                )
                techniques_cfg.setdefault(
                    "max_workers", getattr(args, "tech_max_workers", 2)
                )
                techniques_cfg.setdefault(
                    "enable_rerank_onnx",
                    getattr(args, "tech_enable_rerank_onnx", False),
                )
                # Run bellman_ford inline by default (avoids ProcessPool spawn overhead on Windows)
                try:
                    if not techniques_cfg.get("inline"):
                        techniques_cfg["inline"] = ["bellman_ford"]
                except Exception:
                    pass
                # Tighter, explicit timeouts for the technique scheduler
                try:
                    # fall back quickly if a process task doesn't complete
                    techniques_cfg.setdefault(
                        "fallback_timeout",
                        float(getattr(args, "tech_fallback_timeout", 5.0) or 5.0),
                    )
                    # guard the entire scan to avoid long waits; tie to per-exchange watchdog when present
                    per_ex_watch = float(
                        getattr(args, "per_exchange_watchdog_sec", 0.0) or 0.0
                    )
                    if per_ex_watch > 0:
                        techniques_cfg.setdefault(
                            "iteration_watchdog_sec", per_ex_watch
                        )
                except Exception:
                    pass
                cfg_for_worker = {"techniques": techniques_cfg}
                # Pass BF tuning knobs so the worker can honor them; also allow
                # verbose cycle logging in Python fallback when requested via YAML.
                try:
                    # Prefer explicit CLI flag, but also honor YAML bf.log_all_cycles
                    yaml_log_all = False
                    try:
                        if cfg_raw and isinstance(cfg_raw, dict):
                            yaml_log_all = bool(
                                cfg_raw.get("bf", {}).get("log_all_cycles", False)
                            )
                    except Exception:
                        yaml_log_all = False
                    cfg_for_worker["bf"] = {
                        "min_net": bf_min_net,
                        "min_hops": int(getattr(args, "bf_min_hops", 0)),
                        "max_hops": int(getattr(args, "bf_max_hops", 0)),
                        "min_net_per_hop": float(
                            getattr(args, "bf_min_net_per_hop", 0.0)
                        ),
                        # Expose a debug option to log all cycles (Python BF fallback)
                        "log_all_cycles": bool(
                            getattr(args, "bf_debug_log_all_cycles", False) or yaml_log_all
                        ),
                    }
                except Exception:
                    pass
                t_delegate_start = time.time()
                tech_res = _scan_arbitrage(ts, payload, cfg_for_worker)
                t_delegate_end = time.time()
                logger.info(
                    f"[TIMING] bf_worker({ex_id}): delegate_engine_techniques {t_delegate_end-t_delegate_start:.3f}s"
                )
                if tech_res:
                    # Map technique ArbResult to legacy BF result schema expected by caller
                    for rec in tech_res:
                        try:
                            net_bps = float(rec.get("net_bps_est", 0.0))
                            net_pct = float(net_bps) / 100.0
                            path = rec.get("cycle") or rec.get("path") or ""
                            # compute hops if possible
                            hops = max(0, (str(path).count("->")))
                            inv_amt = float(
                                inv_amt_effective
                                if "inv_amt_effective" in locals()
                                else float(args.inv)
                            )
                            est_after = (
                                round(inv_amt * (1.0 + net_pct / 100.0), 6)
                                if inv_amt is not None
                                else None
                            )
                            local_results.append(
                                {
                                    "exchange": ex_id,
                                    "path": path,
                                    "net_pct": round(net_pct, 4),
                                    "inv": inv_amt,
                                    "est_after": est_after,
                                    "hops": hops,
                                    "iteration": it,
                                    "ts": ts,
                                    **(
                                        {"fee_bps_total": rec.get("fee_bps_total")}
                                        if rec.get("fee_bps_total") is not None
                                        else {}
                                    ),
                                }
                            )
                        except Exception:
                            # best-effort mapping per record
                            local_results.append(
                                {
                                    "exchange": ex_id,
                                    "path": rec.get("cycle") or rec.get("path"),
                                    "ts": ts,
                                }
                            )
                    t_delegate_total = time.time()
                    logger.info(
                        f"[TIMING] bf_worker({ex_id}): total {t_delegate_total-t0_total:.3f}s"
                    )
                    return ex_id, local_lines, local_results
            except Exception:
                logger.debug(
                    "bf_worker: delegation to engine_techniques failed; no legacy BF available"
                )
                t_delegate_total = time.time()
                logger.info(
                    f"[TIMING] bf_worker({ex_id}): total {t_delegate_total-t0_total:.3f}s (fail)"
                )
                # We intentionally removed the legacy BF implementation.
                # If delegation to engine_techniques fails or is disabled, return no results.
                return ex_id, local_lines, local_results
        t_delegate_total = time.time()
        logger.info(
            f"[TIMING] bf_worker({ex_id}): total {t_delegate_total-t0_total:.3f}s (no techniques)"
        )
        return ex_id, local_lines, local_results

    def tri_worker(ex_id: str, it: int, ts: str) -> Tuple[str, List[str], List[dict]]:
        """Per-exchange triangular worker (optimized).
        Collects results in-memory and returns them; caller performs IO/aggregation.
        Optimizations implemented:
        - Bind frequently used attributes to locals
        - Pre-filter tokens and apply blacklist early
        - Precompute QUOTE->X and Y->QUOTE rates (r1_map, r3_map)
        - Iterate pairs using itertools.permutations
        - Use datetime.utcnow() once per worker for timestamps
        - Compute fee_bps_total once
        - Avoid file I/O inside the inner loop
        """
        local_lines: List[str] = []
        local_results: List[dict] = []
        try:
            # Load markets/tickers depending on mode
            if getattr(args, "offline", False):
                ex = None
                markets = None
                tickers = {}
                if offline_snapshot_map and isinstance(offline_snapshot_map, dict):
                    m = offline_snapshot_map.get(ex_id, {})
                    markets = m.get("markets")
                    tickers = m.get("tickers", {})
                if not markets:
                    # nothing to scan in offline mode for this exchange
                    return ex_id, local_lines, local_results
            else:
                # Online mode: create exchange and fetch live data
                ex = load_exchange(ex_id, args.timeout)
                if not safe_has(ex, "fetchTickers"):
                    return ex_id, local_lines, local_results
                markets = ex.load_markets()
                tickers = ex.fetch_tickers()

            ex_norm = normalize_ccxt_id(ex_id)
            # Be robust if swaps_blacklist_map is not yet defined
            try:
                _sbm = swaps_blacklist_map if isinstance(swaps_blacklist_map, dict) else {}
            except Exception:
                _sbm = {}
            exchange_blacklist = _sbm.get(ex_norm, set())

            # Bind frequently used attrs to locals for speed. Allow per-exchange
            # overrides via exchange_overrides_map loaded from YAML.
            tri_min_quote_vol = float(
                _apply_exchange_override(
                    "tri_", ex_id, "min_quote_vol", args.tri_min_quote_vol
                )
            )
            tri_require_top = bool(
                _apply_exchange_override(
                    "tri_", ex_id, "require_topofbook", args.tri_require_topofbook
                )
            )
            tri_fee = float(
                _apply_exchange_override("tri_", ex_id, "fee", args.tri_fee)
            )
            tri_min_net = float(
                _apply_exchange_override("tri_", ex_id, "min_net", args.tri_min_net)
            )
            tri_limit = int(
                _apply_exchange_override(
                    "tri_", ex_id, "currencies_limit", args.tri_currencies_limit
                )
            )
            tri_latency_penalty = float(
                _apply_exchange_override(
                    "tri_",
                    ex_id,
                    "latency_penalty_bps",
                    getattr(args, "tri_latency_penalty_bps", 0.0),
                )
            )
            tri_time_budget = float(
                _apply_exchange_override(
                    "tri_",
                    ex_id,
                    "time_budget_sec",
                    getattr(args, "tri_time_budget_sec", 0.0),
                )
            )
            _pair_is_blacklisted_local = _pair_is_blacklisted
            get_rate_and_qvol_local = get_rate_and_qvol
            # removed unused `json_dumps` assignment

            # Build tokens list with early filtering
            tokens_list: List[str] = []
            seen_tokens: set = set()
            for s, m in markets.items():
                if not m.get("active", True):
                    continue
                base = str(m.get("base") or "").upper()
                quote = str(m.get("quote") or "").upper()
                if not base or not quote:
                    continue
                if base == QUOTE or quote == QUOTE:
                    other = quote if base == QUOTE else base
                    if not other:
                        continue
                    other_up = str(other).upper()
                    if other_up in seen_tokens:
                        continue
                    # apply blacklist early (anchor-quote pair)
                    if exchange_blacklist and _pair_is_blacklisted_local(
                        exchange_blacklist, QUOTE, other_up
                    ):
                        continue
                    seen_tokens.add(other_up)
                    tokens_list.append(other_up)
            # cap tokens
            tokens = tokens_list[:tri_limit]
            try:
                logger.info("[TRI-DBG] %s tokens_for_quote(%s)=%d", ex_id, QUOTE, len(tokens))
            except Exception:
                pass
            if not tokens:
                return ex_id, local_lines, local_results

            # Precompute r1_map and r3_map
            r1_map: Dict[str, tuple] = {}
            r3_map: Dict[str, tuple] = {}
            fee = tri_fee
            for tkn in tokens:
                r1_map[tkn] = get_rate_and_qvol_local(
                    QUOTE, tkn, tickers, fee, tri_require_top
                )
                r3_map[tkn] = get_rate_and_qvol_local(
                    tkn, QUOTE, tickers, fee, tri_require_top
                )

            # Local helpers
            from datetime import datetime
            from itertools import permutations

            ts_now = datetime.utcnow().isoformat()
            fee_bps_total = 3.0 * fee

            # Try delegating triangular scan to engine_techniques if enabled.
            try:
                from .engine_techniques import scan_arbitrage as _scan_arbitrage

                cfg_for_worker = {
                    "techniques": {
                        "enabled": getattr(args, "techniques_enabled", ["stat_tri"]),
                        "max_workers": getattr(args, "tech_max_workers", 2),
                        "enable_rerank_onnx": getattr(
                            args, "tech_enable_rerank_onnx", False
                        ),
                        # Run stat_tri inline to avoid ProcessPool spawn/IPC delays
                        "inline": ["stat_tri"],
                        # Keep tight timeouts in case future expansion adds pool usage
                        "fallback_timeout": float(getattr(args, "tech_fallback_timeout", 5.0) or 5.0),
                        "iteration_watchdog_sec": float(getattr(args, "per_exchange_watchdog_sec", 0.0) or 10.0),
                        # optional time budget for stat_tri inner loop
                        "tri_time_budget_sec": float(getattr(args, "tri_time_budget_sec", 0.0) or 0.0),
                    }
                }
                # Build a compact, serializable payload for stat_tri
                payload = {
                    "ex_id": ex.id,
                    "quote": QUOTE,
                    "tokens": tokens,
                    "tickers": tickers,
                    "fee": fee,
                    "require_top": tri_require_top,
                    "min_quote_vol": tri_min_quote_vol,
                    "min_net": tri_min_net,
                    "latency_penalty": tri_latency_penalty,
                    "ts": ts_now,
                    "time_budget_sec": float(tri_time_budget or 0.0),
                }
                tech_res = _scan_arbitrage(ts_now, payload, cfg_for_worker)
                if tech_res:
                    # engine_techniques returns ArbResult-like dicts; extend local_results and return
                    for rec in tech_res:
                        local_results.append(rec)
                    return ex_id, local_lines, local_results
            except Exception:
                # Fall back to in-process triangular loop if delegation fails
                logger.debug(
                    "tri_worker: delegation to engine_techniques failed; falling back"
                )

            # Iterate pairs using permutations (X, Y)
            loop_start = time.time()
            for X, Y in permutations(tokens, 2):
                # enforce optional time budget
                if tri_time_budget and (time.time() - loop_start) >= tri_time_budget:
                    break
                # skip blacklisted pair X->Y
                if exchange_blacklist and _pair_is_blacklisted_local(
                    exchange_blacklist, X, Y
                ):
                    continue

                r1, qv1 = r1_map.get(X, (None, None))
                if not r1:
                    continue
                if tri_min_quote_vol > 0 and (qv1 is None or qv1 < tri_min_quote_vol):
                    continue

                r2, qv2 = get_rate_and_qvol_local(X, Y, tickers, fee, tri_require_top)
                if not r2:
                    continue
                if tri_min_quote_vol > 0 and (qv2 is None or qv2 < tri_min_quote_vol):
                    continue

                r3, qv3 = r3_map.get(Y, (None, None))
                if not r3:
                    continue
                if tri_min_quote_vol > 0 and (qv3 is None or qv3 < tri_min_quote_vol):
                    continue

                gross_bps = (r1 * r2 * r3 - 1.0) * 10000.0
                net_bps = gross_bps - fee_bps_total
                if net_bps >= tri_min_net:
                    rec = {
                        "ts": ts_now,
                        "venue": ex.id,
                        "cycle": f"{QUOTE}->{X}->{Y}->{QUOTE}",
                        "net_bps_est": round(net_bps - tri_latency_penalty, 4),
                        "fee_bps_total": fee_bps_total,
                        "status": "actionable",
                    }
                    local_results.append(rec)
        except Exception as e:
            logger.debug("tri_worker fallo %s: %s", ex_id, e)
            return ex_id, local_lines, local_results
        # Normal successful completion: return any collected results
        return ex_id, local_lines, local_results

    # (removed fallback minimal BF loop that prematurely returned and bypassed the full BF rendering path)

    # Correct BF main loop (logs + history). This sits at the BF-block level, not inside bf_worker.
    iteration_watchdog_sec = float(getattr(args, "iteration_watchdog_sec", 0.0) or 0.0)
    _prev_iter_ts = None
    logger.info("[DEBUG] Entrando al ciclo principal BF...")
    for it in range(1, int(max(1, args.repeat)) + 1):
        logger.info(f"[DEBUG] Iteración BF número: {it}")
        t_iter_start = time.time()
        logger.info(f"[TIMING] BF iter {it}: start")
        _now = time.time()
        if _prev_iter_ts is not None and iteration_watchdog_sec > 0:
            _delta = _now - _prev_iter_ts
            if _delta > iteration_watchdog_sec:
                logger.error(
                    "Iteration watchdog triggered (bf): previous iteration "
                    "start delta=%.2fs > configured %.2fs; exiting",
                    _delta,
                    iteration_watchdog_sec,
                )
                print(
                    f"Iteration watchdog (bf): delayed by {_delta:.2f}s "
                    f"(limit {iteration_watchdog_sec}s). Exiting."
                )
                break
        _prev_iter_ts = _now
        ts = pd.Timestamp.utcnow().isoformat()
        swaps_blacklist_map = load_swaps_blacklist()
        t_prefetch_start = time.time()
        # Prefetch wallet balances once per iteration for simulation/header if requested
        try:
            if args.simulate_compound and getattr(args, "simulate_from_wallet", False):
                wallet_buckets_cache = _prefetch_wallet_buckets(list(EX_IDS), args)
            else:
                wallet_buckets_cache = {}
        except Exception:
            wallet_buckets_cache = {}
        t_prefetch_end = time.time()
        logger.info(
            f"[TIMING] BF iter {it}: prefetch_wallet_buckets {t_prefetch_end-t_prefetch_start:.3f}s"
        )
        # Hydrate simulation balances from wallet snapshot once (first iteration) if requested
        t_hydrate_start = time.time()
        try:
            if (
                args.simulate_compound
                and getattr(args, "simulate_from_wallet", False)
                and it == 1
                and wallet_buckets_cache
            ):
                for ex_id in EX_IDS:
                    st = sim_state.get(ex_id)
                    if not st:
                        continue
                    wb = wallet_buckets_cache.get(ex_id) or {}
                    usdt = float(wb.get("USDT", 0.0) or 0.0)
                    usdc = float(wb.get("USDC", 0.0) or 0.0)
                    prefer = str(
                        getattr(args, "simulate_prefer", "auto") or "auto"
                    ).upper()
                    chosen_ccy = st.get("ccy") or "USDT"
                    chosen_bal = 0.0
                    if prefer == "USDT":
                        chosen_ccy, chosen_bal = "USDT", usdt
                    elif prefer == "USDC":
                        chosen_ccy, chosen_bal = "USDC", usdc
                    else:
                        if usdt >= usdc and usdt > 0:
                            chosen_ccy, chosen_bal = "USDT", usdt
                        elif usdc > 0:
                            chosen_ccy, chosen_bal = "USDC", usdc
                        else:
                            chosen_ccy, chosen_bal = (st.get("ccy") or "USDT"), 0.0
                    sim_state[ex_id] = {
                        "ccy": chosen_ccy,
                        "balance": float(chosen_bal),
                        "start_balance": float(chosen_bal),
                        "start_ccy": chosen_ccy,
                    }
        except Exception:
            pass
        t_hydrate_end = time.time()
        logger.info(
            f"[TIMING] BF iter {it}: hydrate_sim_balances {t_hydrate_end-t_hydrate_start:.3f}s"
        )
        t_console_start = time.time()
        if do_console_clear:
            try:
                if os.name == "nt":
                    os.system("cls")
                else:
                    print("\033[2J\033[H", end="")
            except Exception:
                pass
        t_console_end = time.time()
        logger.info(
            f"[TIMING] BF iter {it}: console_clear {t_console_end-t_console_start:.3f}s"
        )
        # Clean per-iteration artifacts and any historical files to avoid mixing iterations
        t_cleanup_start = time.time()
        try:
            if current_file.exists():
                current_file.unlink()  # type: ignore[arg-type]
        except Exception:
            pass
        try:
            if bf_iter_csv.exists():
                bf_iter_csv.unlink()  # type: ignore[arg-type]
        except Exception:
            pass
        # Do not remove bf_history.txt: we now keep accumulation across iterations
        try:
            if bf_top_hist_csv.exists():
                bf_top_hist_csv.unlink()  # type: ignore[arg-type]
        except Exception:
            pass
        t_cleanup_end = time.time()
        logger.info(
            f"[TIMING] BF iter {it}: cleanup {t_cleanup_end-t_cleanup_start:.3f}s"
        )
        # Create snapshot header
        try:
            with open(current_file, "w", encoding="utf-8") as fh:
                fh.write(f"[BF] Iteración {it}/{args.repeat} @ {ts}\n\n")
                # Always display Simulation (estado actual) first, right after the header (guarded by UI flag)
                if getattr(args, "ui_show_simulation_header_always", True):
                    fh.write("Simulación (estado actual)\n")
                    # Build rows with robust fallbacks so this section is never empty
                    rows_sim_hdr = []
                    try:
                        rows_sim_hdr = (
                            _build_simulation_rows(
                                sim_state, args, wallet_buckets_cache
                            )
                            or []
                        )
                    except Exception:
                        rows_sim_hdr = []
                    if not rows_sim_hdr:
                        # Fallback: one row per exchange to avoid empty section
                        try:
                            for ex_id_fb in EX_IDS:
                                ccy_fb = (
                                    str(sim_state.get(ex_id_fb, {}).get("ccy", QUOTE))
                                    if isinstance(sim_state.get(ex_id_fb), dict)
                                    else QUOTE
                                )
                                rows_sim_hdr.append(
                                    {
                                        "exchange": ex_id_fb,
                                        "currency": ccy_fb,
                                        "start_balance": 0.0,
                                        "balance": 0.0,
                                        "profit": 0.0,
                                        "roi_pct": 0.0,
                                    }
                                )
                        except Exception:
                            rows_sim_hdr = []
                    # Try pretty table; if that fails, render a minimal markdown table
                    try:
                        df_sim_hdr = pd.DataFrame(rows_sim_hdr)
                        fh.write(
                            tabulate(
                                df_sim_hdr,
                                headers="keys",
                                tablefmt="github",
                                showindex=False,
                            )
                        )
                    except Exception:
                        headers = [
                            "exchange",
                            "currency",
                            "start_balance",
                            "balance",
                            "profit",
                            "roi_pct",
                        ]
                        fh.write("| " + " | ".join(headers) + " |\n")
                        fh.write(
                            "|" + "|".join(["-" * len(h) for h in headers]) + "|\n"
                        )
                        for r in rows_sim_hdr:
                            fh.write(
                                "| "
                                + " | ".join(
                                    [
                                        str(r.get("exchange", "")),
                                        str(r.get("currency", "")),
                                        f"{float(r.get('start_balance',0.0)):.4f}",
                                        f"{float(r.get('balance',0.0)):.4f}",
                                        f"{float(r.get('profit',0.0)):.4f}",
                                        f"{float(r.get('roi_pct',0.0)):.4f}",
                                    ]
                                )
                                + " |\n"
                            )
                    fh.write("\n")
                if getattr(args, "ui_progress_bar", True):
                    total_ex = max(1, len(EX_IDS))
                    completed = 0
                    frames = str(getattr(args, "ui_spinner_frames", "|/-\\"))
                    bar_len = int(getattr(args, "ui_progress_len", 20))
                    filled = int(bar_len * completed / total_ex)
                    bar = "[" + ("#" * filled) + ("-" * (bar_len - filled)) + "]"
                    try:
                        spinner = frames[completed % len(frames)] if frames else ""
                    except Exception:
                        spinner = ""
                    fh.write("Progreso\n")
                    fh.write(f"{bar} {completed}/{total_ex} {spinner}\n\n")
                fh.write("Detalle (progreso)\n")
            _sync_snapshot_alias()
        except Exception:
            pass

        iter_lines: List[str] = []
        iter_results: List[dict] = []
        completed_count = 0
        # Timeout duro por exchange usando ThreadPoolExecutor
        import concurrent.futures

        per_exchange_watchdog_sec = float(
            getattr(args, "per_exchange_watchdog_sec", 0.0) or 0.0
        )
        if per_exchange_watchdog_sec <= 0:
            per_exchange_watchdog_sec = float(
                getattr(args, "iteration_watchdog_sec", 0.0) or 0.0
            )
        t_threadpool_start = time.time()
        logger.info(f"[TIMING] BF iter {it}: ThreadPoolExecutor start")
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            # Map futures to (exchange id, submit_ts) to compute realistic durations
            future_map = {}
            for ex_id in EX_IDS:
                _submit_ts = time.time()
                future = executor.submit(bf_worker, ex_id, it, ts)
                future_map[future] = (ex_id, _submit_ts)
            pending = set(future_map.keys())
            iter_watchdog = float(getattr(args, "iteration_watchdog_sec", 0.0) or 0.0)
            loop_start = time.time()
            _interrupted = False
            try:
                while pending:
                    # hard iteration watchdog across all futures
                    if iter_watchdog and (time.time() - loop_start) >= iter_watchdog:
                        logger.error(
                            "BF main watchdog fired after %.2fs; cancelling %d pending",
                            iter_watchdog,
                            len(pending),
                        )
                        for fut in list(pending):
                            try:
                                fut.cancel()
                            except Exception:
                                pass
                        pending.clear()
                        break

                    done, still_pending = concurrent.futures.wait(
                        pending,
                        timeout=(
                            per_exchange_watchdog_sec
                            if per_exchange_watchdog_sec > 0
                            else None
                        ),
                        return_when=concurrent.futures.FIRST_COMPLETED,
                    )
                    # Process any completed futures
                    for future in list(done):
                        pending.discard(future)
                        ex_id, _submit_ts = future_map.get(future, ("<unknown>", None))
                        try:
                            _wait_start = time.time()
                            _ex_id, lines, rows = future.result(timeout=0)
                            _end_ts = time.time()
                            _ex_dur = max(0.0, _end_ts - (_submit_ts or _wait_start))
                            logger.info(
                                f"[TIMING] BF iter {it}: {ex_id} worker duration: {_ex_dur:.3f}s"
                            )
                        except concurrent.futures.TimeoutError:
                            logger.error(
                                "Exchange watchdog: %s timed out after %.2fs; skipping.",
                                ex_id,
                                per_exchange_watchdog_sec,
                            )
                            print(
                                f"Exchange watchdog: {ex_id} timed out after {per_exchange_watchdog_sec:.2f}s. Skipping."
                            )
                            continue
                        except Exception as e:
                            logger.error("Exchange %s failed: %s", ex_id, e)
                            continue
                        iter_lines.extend(lines)
                        iter_results.extend(rows)
                        completed_count += 1
                        # Update persistence stats for each discovered opportunity row now
                        try:
                            for row in rows:
                                key = (row.get("exchange"), row.get("path"))
                                if not key[0] or not key[1]:
                                    continue
                                st = persistence.get(key)
                                if not st:
                                    persistence[key] = {
                                        "first_seen": ts,
                                        "last_seen": ts,
                                        "occurrences": 1,
                                        "current_streak": 1,
                                        "max_streak": 1,
                                        "last_it": it,
                                    }
                                else:
                                    st["last_seen"] = ts
                                    st["occurrences"] = (
                                        int(st.get("occurrences", 0)) + 1
                                    )
                                    prev_it = int(st.get("last_it", 0))
                                    if prev_it + 1 == it:
                                        st["current_streak"] = (
                                            int(st.get("current_streak", 0)) + 1
                                        )
                                    else:
                                        st["current_streak"] = 1
                                    st["max_streak"] = max(
                                        int(st.get("max_streak", 0)),
                                        int(st.get("current_streak", 0)),
                                    )
                                    st["last_it"] = it
                                results_bf.append(row)
                        except Exception:
                            pass
                        if getattr(args, "ui_progress_bar", True):
                            try:
                                total_ex = max(1, len(EX_IDS))
                                frames = str(
                                    getattr(args, "ui_spinner_frames", "|/-\\")
                                )
                                bar_len = int(getattr(args, "ui_progress_len", 20))
                                filled = int(bar_len * completed_count / total_ex)
                                bar = (
                                    "["
                                    + ("#" * filled)
                                    + ("-" * (bar_len - filled))
                                    + "]"
                                )
                                spinner = (
                                    frames[completed_count % len(frames)]
                                    if frames
                                    else ""
                                )
                                # Open snapshot and append progress line safely
                                with open(current_file, "a", encoding="utf-8") as _fhp:
                                    _fhp.write(
                                        f"{bar} {completed_count}/{total_ex} {spinner}\n"
                                    )
                            except Exception:
                                pass

                    # Cancel any futures that exceeded per-exchange watchdog
                    if per_exchange_watchdog_sec > 0:
                        now_ts = time.time()
                        for fut in list(still_pending):
                            ex_id, submit_ts = future_map.get(
                                fut, ("<unknown>", now_ts)
                            )
                            if (
                                submit_ts
                                and (now_ts - submit_ts) >= per_exchange_watchdog_sec
                            ):
                                try:
                                    fut.cancel()
                                except Exception:
                                    pass
                                pending.discard(fut)
                                logger.error(
                                    "Exchange watchdog: %s timed out after %.2fs; cancelled.",
                                    ex_id,
                                    per_exchange_watchdog_sec,
                                )
            except KeyboardInterrupt:
                # Graceful interrupt: cancel all pending and finish this iteration cleanly
                _interrupted = True
                try:
                    for fut in list(pending):
                        try:
                            fut.cancel()
                        except Exception:
                            pass
                    pending.clear()
                finally:
                    logger.warning(
                        "KeyboardInterrupt during BF wait; finishing iteration and exiting run."
                    )
                # removed: invalid out-of-scope 'rows' processing; handled above per-future
        t_threadpool_end = time.time()
        logger.info(
            f"[TIMING] BF iter {it}: ThreadPoolExecutor total {t_threadpool_end-t_threadpool_start:.3f}s"
        )
        try:
            with open(current_file, "a", encoding="utf-8") as fh:
                if getattr(args, "ui_progress_bar", True):
                    # Do not bump completed_count again here; it already reflects finished workers
                    total_ex = max(1, len(EX_IDS))
                    frames = str(getattr(args, "ui_spinner_frames", "|/-\\"))
                    bar_len = int(getattr(args, "ui_progress_len", 20))
                    filled = int(bar_len * completed_count / total_ex)
                    bar = "[" + ("#" * filled) + ("-" * (bar_len - filled)) + "]"
                    try:
                        spinner = (
                            frames[completed_count % len(frames)] if frames else ""
                        )
                    except Exception:
                        spinner = ""
                    fh.write(f"{bar} {completed_count}/{total_ex} {spinner}\n")
                if iter_lines:
                    fh.write("\n" + "\n".join(iter_lines) + "\n")
                fh.flush()
            _sync_snapshot_alias()
        except Exception:
            pass

        # Persist per-iteration top-k CSV (optional)
        try:
            if args.bf_persist_top_csv and iter_results:
                df_top = (
                    pd.DataFrame(iter_results)
                    .sort_values("net_pct", ascending=False)
                    .head(max(1, int(args.bf_top)))
                )
                df_top.to_csv(bf_top_hist_csv, index=False)
        except Exception:
            pass
        # Overwrite current-iteration CSV
        try:
            if iter_results:
                pd.DataFrame(iter_results).to_csv(bf_iter_csv, index=False)
            else:
                pd.DataFrame(
                    columns=[
                        "exchange",
                        "path",
                        "net_pct",
                        "inv",
                        "est_after",
                        "hops",
                        "iteration",
                        "ts",
                    ]
                ).to_csv(bf_iter_csv, index=False)
        except Exception:
            pass
        # Append final aggregated sections to snapshot
        try:
            with open(current_file, "a", encoding="utf-8") as fh:
                fh.write("\n---\nResumen final (iteración)\n\n")
            try:
                if iter_results:
                    df_iter = pd.DataFrame(iter_results)
                    df_top = df_iter.sort_values("net_pct", ascending=False).head(
                        max(1, int(args.bf_top))
                    )
                    cols_top = [
                        c
                        for c in [
                            "exchange",
                            "path",
                            "hops",
                            "net_pct",
                            "inv",
                            "est_after",
                            "ts",
                        ]
                        if c in df_top.columns
                    ]
                    fh.write("TOP oportunidades (iteración)\n")
                    fh.write(
                        tabulate(
                            df_top[cols_top],
                            headers="keys",
                            tablefmt="github",
                            showindex=False,
                        )
                    )
                    fh.write("\n\n")
                else:
                    fh.write("TOP oportunidades (iteración): (sin resultados)\n\n")
            except Exception:
                fh.write("TOP oportunidades (iteración): (error al generar tabla)\n\n")
            try:
                if iter_results:
                    df_iter = pd.DataFrame(iter_results)
                    grp = df_iter.groupby("exchange", as_index=False).agg(
                        count=("net_pct", "count"), best_net=("net_pct", "max")
                    )
                    grp = grp.sort_values(
                        ["best_net", "count"], ascending=[False, False]
                    )
                    fh.write("Resumen por exchange (iteración)\n")
                    fh.write(
                        tabulate(
                            grp, headers="keys", tablefmt="github", showindex=False
                        )
                    )
                    fh.write("\n\n")
            except Exception:
                pass
            if iter_lines:
                fh.write("Detalle (iteración, completo)\n")
                fh.write("\n".join(iter_lines) + "\n")
            else:
                fh.write("(sin oportunidades en esta iteración)\n")
        except Exception:
            pass
        _sync_snapshot_alias()
        t_iter_end = time.time()
        logger.info(
            f"[TIMING] BF iter {it}: total iteration {t_iter_end-t_iter_start:.3f}s"
        )
        # Sleep only between iterations
        if it < args.repeat:
            t_sleep_start = time.time()
            # Simple sleep between iterations; the next loop iteration will recreate headers and rerun
            time.sleep(max(0.0, args.repeat_sleep))
            t_sleep_end = time.time()
            logger.info(
                f"[TIMING] BF iter {it}: sleep {t_sleep_end-t_sleep_start:.3f}s"
            )
        # If user interrupted during wait loop, exit outer repeat loop after finalizing this iteration
        try:
            if _interrupted:
                logger.info("BF run interrupted by user at iteration %d; exiting.", it)
                break
        except Exception:
            pass
        # continue  # removed to allow simulation and summaries to run within the same loop

        # Simulation: per-exchange selection and compounding
        if args.simulate_compound and sim_state:
            # Group results by exchange
            results_by_ex: Dict[str, List[dict]] = {}
            for row in iter_results:
                ex_id = row.get("exchange")
                if not ex_id:
                    continue
                results_by_ex.setdefault(ex_id, []).append(row)
            for ex_id in EX_IDS:
                st = sim_state.get(ex_id)
                if not st:
                    continue
                ccy = str(st.get("ccy") or QUOTE)
                balance = float(st.get("balance") or 0.0)
                rows_ex = results_by_ex.get(ex_id, [])
                selected = None
                if rows_ex:

                    def ends_with_ccy(r: dict, c: str) -> bool:
                        try:
                            parts = str(r.get("path") or "").split("->")
                            # Allow any starting asset; require the path to end at the anchor currency
                            return len(parts) >= 2 and parts[-1].upper() == c.upper()
                        except Exception:
                            return False

                    # Best per anchor for this exchange
                    best_per_anchor: Dict[str, dict] = {}
                    anchors_iter = (
                        set([a for a in allowed_quotes]) if allowed_quotes else {QUOTE}
                    )
                    for anc in anchors_iter:
                        anc_cands = [r for r in rows_ex if ends_with_ccy(r, anc)]
                        if not anc_cands:
                            continue
                        if args.simulate_select == "first":
                            best_per_anchor[anc] = anc_cands[0]
                        else:
                            best_per_anchor[anc] = max(
                                anc_cands,
                                key=lambda r: float(r.get("net_pct", 0.0)),
                            )
                    current_best = best_per_anchor.get(ccy)
                    chosen_anchor = ccy
                    chosen_row = current_best
                    if args.simulate_auto_switch and best_per_anchor:
                        overall_anchor, overall_row = None, None
                        for anc, row in best_per_anchor.items():
                            if overall_row is None or float(
                                row.get("net_pct", 0.0)
                            ) > float(overall_row.get("net_pct", 0.0)):
                                overall_anchor, overall_row = anc, row
                        if overall_row is not None:
                            cur_net = (
                                float(current_best.get("net_pct", 0.0))
                                if current_best
                                else -1e9
                            )
                            over_net = float(overall_row.get("net_pct", 0.0))
                            if (
                                current_best is None
                                or (over_net - cur_net)
                                >= float(args.simulate_switch_threshold) - 1e-12
                            ):
                                chosen_anchor, chosen_row = (
                                    overall_anchor,
                                    overall_row,
                                )
                    if chosen_row is not None:
                        if chosen_anchor != ccy:
                            # Anchor change is useful but keep it silent at INFO level to avoid [SIM] duplication
                            logger.debug(
                                "Cambio de ancla @%s: %s -> %s (mejor net%%)",
                                ex_id,
                                ccy,
                                chosen_anchor,
                            )
                            ccy = chosen_anchor
                        selected = chosen_row
                if selected is not None:
                    product = 1.0 + (float(selected.get("net_pct", 0.0)) / 100.0)
                    before = balance
                    after = round(before * product, 8)
                    gain_amt = round(after - before, 8)
                    gain_pct = round((product - 1.0) * 100.0, 6)
                    sim_rows.append(
                        {
                            "iteration": it,
                            "ts": ts,
                            "exchange": ex_id,
                            "path": selected.get("path"),
                            "hops": selected.get("hops"),
                            "net_pct": float(selected.get("net_pct", 0.0)),
                            "product": round(product, 12),
                            "balance_before": before,
                            "balance_after": after,
                            "gain_amount": gain_amt,
                            "gain_pct": gain_pct,
                            "currency": ccy,
                        }
                    )
                    # Update state (preserve start_balance/start_ccy)
                    prev = sim_state.get(ex_id, {})
                    sim_state[ex_id] = {
                        "ccy": ccy,
                        "balance": after,
                        "start_balance": float(prev.get("start_balance", 0.0) or 0.0),
                        "start_ccy": prev.get("start_ccy", ccy),
                    }
                    line = (
                        f"[SIM] it#{it} @{ex_id} {ccy} pick {selected.get('path')} net {gain_pct:.4f}% "
                        f"| {ccy} {before:.4f} -> {after:.4f} (+{gain_amt:.4f})"
                    )
                else:
                    line = None
                if line:
                    # Do not log [SIM] lines via logger; keep them only in current_bf.txt and CSV
                    iter_lines.append(line)

        try:
            # Persist per-iteration top-k (optional)
            if args.bf_persist_top_csv:
                try:
                    # pick top by net_pct across all lines parsed in this iteration (iter_results)
                    if iter_results:
                        df_top = pd.DataFrame(iter_results)
                        df_top = df_top.sort_values("net_pct", ascending=False).head(
                            max(1, int(args.bf_top))
                        )
                        # Overwrite file every iteration (no historical accumulation)
                        df_top.to_csv(bf_top_hist_csv, index=False)
                except Exception:
                    pass
            # Overwrite the current-iteration CSV with this iteration's results
            try:
                if iter_results:
                    pd.DataFrame(iter_results).to_csv(bf_iter_csv, index=False)
                else:
                    pd.DataFrame(
                        columns=[
                            "exchange",
                            "path",
                            "net_pct",
                            "inv",
                            "est_after",
                            "hops",
                            "iteration",
                            "ts",
                        ]
                    ).to_csv(bf_iter_csv, index=False)
            except Exception:
                pass
            # Snapshot file: append final aggregated sections (keep earlier progress)
            with open(current_file, "a", encoding="utf-8") as fh:
                fh.write("\n---\nResumen final (iteración)\n\n")
                # 1) Top oportunidades de la iteración
                try:
                    if iter_results:
                        df_iter = pd.DataFrame(iter_results)
                        df_top = df_iter.sort_values("net_pct", ascending=False).head(
                            max(1, int(args.bf_top))
                        )
                        cols_top = [
                            c
                            for c in [
                                "exchange",
                                "path",
                                "hops",
                                "net_pct",
                                "inv",
                                "est_after",
                                "ts",
                            ]
                            if c in df_top.columns
                        ]
                        fh.write("TOP oportunidades (iteración)\n")
                        fh.write(
                            tabulate(
                                df_top[cols_top],
                                headers="keys",
                                tablefmt="github",
                                showindex=False,
                            )
                        )
                        fh.write("\n\n")
                    else:
                        fh.write("TOP oportunidades (iteración): (sin resultados)\n\n")
                except Exception:
                    fh.write(
                        "TOP oportunidades (iteración): (error al generar tabla)\n\n"
                    )
                # 2) Resumen por exchange de la iteración
                try:
                    if iter_results:
                        df_iter = pd.DataFrame(iter_results)
                        grp = df_iter.groupby("exchange", as_index=False).agg(
                            count=("net_pct", "count"), best_net=("net_pct", "max")
                        )
                        grp = grp.sort_values(
                            ["best_net", "count"], ascending=[False, False]
                        )
                        fh.write("Resumen por exchange (iteración)\n")
                        fh.write(
                            tabulate(
                                grp,
                                headers="keys",
                                tablefmt="github",
                                showindex=False,
                            )
                        )
                        fh.write("\n\n")
                except Exception:
                    pass
                # 3) Resumen de simulación (estado actual)
                try:
                    if args.simulate_compound and sim_state:
                        rows_sim = _build_simulation_rows(
                            sim_state, args, wallet_buckets_cache
                        )
                        if rows_sim:
                            df_sim = pd.DataFrame(rows_sim)
                            fh.write("Simulación (estado actual)\n")
                            fh.write(
                                tabulate(
                                    df_sim,
                                    headers="keys",
                                    tablefmt="github",
                                    showindex=False,
                                )
                            )
                            fh.write("\n\n")
                except Exception:
                    pass
                # 4) Persistencia (top por racha)
                try:
                    if persistence:
                        prow = []
                        for (ex_id, path_str), st in persistence.items():
                            prow.append(
                                {
                                    "exchange": ex_id,
                                    "path": path_str,
                                    "occurrences": int(st.get("occurrences", 0)),
                                    "current_streak": int(st.get("current_streak", 0)),
                                    "max_streak": int(st.get("max_streak", 0)),
                                    "last_seen": st.get("last_seen"),
                                }
                            )
                        if prow:
                            dfp = pd.DataFrame(prow)
                            dfp = dfp.sort_values(
                                ["max_streak", "occurrences"],
                                ascending=[False, False],
                            ).head(10)
                            cols_p = [
                                c
                                for c in [
                                    "exchange",
                                    "path",
                                    "occurrences",
                                    "current_streak",
                                    "max_streak",
                                    "last_seen",
                                ]
                                if c in dfp.columns
                            ]
                            fh.write("Persistencia (top)\n")
                            fh.write(
                                tabulate(
                                    dfp[cols_p],
                                    headers="keys",
                                    tablefmt="github",
                                    showindex=False,
                                )
                            )
                            fh.write("\n\n")
                except Exception:
                    pass
                # 5) Detalle texto final (incluye [SIM] picks por iteración)
                # Ya se fueron agregando líneas de progreso; añadimos el detalle completo al final por conveniencia
                if iter_lines:
                    fh.write("Detalle (iteración, completo)\n")
                    fh.write("\n".join(iter_lines) + "\n")
                else:
                    fh.write("(sin oportunidades en esta iteración)\n")
            # Mirror snapshot alias so both filenames stay in sync
            _sync_snapshot_alias()
            # History file: append all iterations to keep a running log
            bf_hist = paths.LOGS_DIR / "bf_history.txt"
            with open(bf_hist, "a", encoding="utf-8") as fh:
                fh.write(f"[BF] Iteración {it}/{args.repeat} @ {ts}\n")
                if iter_lines:
                    fh.write("\n".join(iter_lines) + "\n\n")
                else:
                    # Si no hubo líneas de simulación/progreso, pero sí hubo resultados,
                    # escribe un resumen compacto para evitar un mensaje vacío engañoso.
                    if 'iter_results' in locals() and iter_results:
                        try:
                            import pandas as _pd
                            _df = _pd.DataFrame(iter_results)
                            _n = len(_df)
                            _best = float(_df["net_pct"].max()) if "net_pct" in _df.columns else 0.0
                            _by_ex = (
                                _df.groupby("exchange", as_index=False)
                                .agg(count=("net_pct", "count"), best_net=("net_pct", "max"))
                                .sort_values(["best_net", "count"], ascending=[False, False])
                            ) if "exchange" in _df.columns else None
                            fh.write(
                                f"(resumen) oportunidades={_n}, mejor_net={_best:.4f}%\n"
                            )
                            if _by_ex is not None and not _by_ex.empty:
                                # Formato ligero por exchange
                                _lines = [
                                    f" - {_row['exchange']}: n={int(_row['count'])}, best={float(_row['best_net']):.4f}%"
                                    for _idx, _row in _by_ex.iterrows()
                                ]
                                fh.write("\n".join(_lines) + "\n\n")
                            else:
                                fh.write("\n")
                        except Exception:
                            fh.write("(resumen) oportunidades encontradas\n\n")
                    else:
                        fh.write("(sin oportunidades en esta iteración)\n\n")
            try:
                logger.info(
                    "BF history append: %s (exists=%s)",
                    str(bf_hist),
                    str(bf_hist.exists()),
                )
            except Exception:
                pass
            # No alias writes for history to avoid duplicates and mixed-case filenames
        except Exception:
            pass
        # (sleep already handled above)
        if results_bf:
            pd.DataFrame(results_bf).to_csv(bf_csv, index=False)
        else:
            pd.DataFrame(
                columns=[
                    "exchange",
                    "path",
                    "net_pct",
                    "inv",
                    "est_after",
                    "hops",
                    "iteration",
                    "ts",
                ]
            ).to_csv(bf_csv, index=False)
            logger.info(
                (
                    "BF: sin oportunidades con los filtros actuales (min_net=%s%%, "
                    "require_topofbook=%s, min_quote_vol=%s). Prueba relajar filtros "
                    "(p.ej. bajar --bf_min_quote_vol, quitar --bf_require_topofbook, "
                    "o bajar --bf_min_net) o aumentar --bf_currencies_limit."
                ),
                args.bf_min_net,
                bool(args.bf_require_topofbook),
                args.bf_min_quote_vol,
            )
        logger.info("BF CSV: %s", bf_csv)
        # Write simulation CSV if enabled
        if args.simulate_compound and sim_rows:
            pd.DataFrame(sim_rows).to_csv(bf_sim_csv, index=False)
            logger.info("BF Simulation CSV: %s", bf_sim_csv)
        # Write simulation summary per exchange (start/end/ROI) if enabled
        if args.simulate_compound and sim_state:
            try:
                summary_rows = []
                for ex_id, st in sim_state.items():
                    try:
                        # Use the true recorded start_balance; no fallback to current balance
                        start_bal = float(st.get("start_balance", 0.0) or 0.0)
                    except Exception:
                        start_bal = 0.0
                    try:
                        end_bal = float(st.get("balance", 0.0) or 0.0)
                    except Exception:
                        end_bal = 0.0
                    ccy = str(st.get("ccy") or QUOTE)
                    start_ccy = str(st.get("start_ccy") or ccy)
                    # Avoid None/N/A in logs: display 0.0 when start balance is zero
                    roi_pct = (
                        ((end_bal - start_bal) / start_bal * 100.0)
                        if start_bal > 0
                        else 0.0
                    )
                    summary_rows.append(
                        {
                            "exchange": ex_id,
                            "start_currency": start_ccy,
                            "start_balance": round(start_bal, 8),
                            "end_currency": ccy,
                            "end_balance": round(end_bal, 8),
                            "roi_pct": None if roi_pct is None else round(roi_pct, 6),
                            # Report the actual last iteration reached, not the configured repeat
                            "iterations": int(it),
                        }
                    )
                bf_sim_summary_csv = (
                    paths.OUTPUTS_DIR
                    / f"arbitrage_bf_simulation_summary_{QUOTE.lower()}_ccxt.csv"
                )
                pd.DataFrame(summary_rows).to_csv(bf_sim_summary_csv, index=False)
                # Log a short summary line per exchange (sorted by ROI desc)
                try:
                    rows_sorted = sorted(
                        summary_rows,
                        key=lambda r: (
                            r["roi_pct"] if r["roi_pct"] is not None else float("-inf")
                        ),
                        reverse=True,
                    )
                except Exception:
                    rows_sorted = summary_rows
                for r in rows_sorted:
                    roi_txt = (
                        f"{(r['roi_pct'] if r['roi_pct'] is not None else 0.0):.4f}%"
                    )
                    logger.info(
                        "BF SIM SUM @%s: %s %.4f -> %s %.4f (ROI %s, it=%d)",
                        r["exchange"],
                        r["start_currency"],
                        r["start_balance"],
                        r["end_currency"],
                        r["end_balance"],
                        roi_txt,
                        r["iterations"],
                    )
                logger.info("BF Simulation Summary CSV: %s", bf_sim_summary_csv)
            except Exception as e:
                logger.warning("No se pudo escribir el resumen de simulación BF: %s", e)
        # Write persistence summary (if any)
        if persistence:
            rows = []
            for (ex_id, path_str), st in persistence.items():
                try:
                    first_ts = pd.to_datetime(st.get("first_seen"))
                    last_ts = pd.to_datetime(st.get("last_seen"))
                    approx_duration_s = max(0.0, (last_ts - first_ts).total_seconds())
                except Exception:
                    approx_duration_s = None
                rows.append(
                    {
                        "exchange": ex_id,
                        "path": path_str,
                        "first_seen": st.get("first_seen"),
                        "last_seen": st.get("last_seen"),
                        "occurrences": st.get("occurrences"),
                        "max_streak": st.get("max_streak"),
                        "approx_duration_s": approx_duration_s,
                    }
                )
            pd.DataFrame(rows).to_csv(bf_persist_csv, index=False)
            logger.info("BF Persistence CSV: %s", bf_persist_csv)
        # Auto-generate per-exchange summary from bf_history (CSV + Markdown)
        try:
            hist_path = str(paths.LOGS_DIR / "bf_history.txt")
            sum_csv = str(paths.OUTPUTS_DIR / "bf_sim_summary.csv")
            sum_md = str(paths.OUTPUTS_DIR / "bf_sim_summary.md")
            _bf_write_history_summary_and_md(hist_path, sum_csv, sum_md)
            logger.info("BF Summary CSV: %s", sum_csv)
            logger.info("BF Summary MD: %s", sum_md)
        except Exception as e:
            logger.warning("No se pudo generar el resumen BF (CSV/MD): %s", e)
        # Do not return here; allow the outer repeat loop to continue to the next iteration

    # ---------------------------
    # INTER-EXCHANGE SPREAD MODE (fallback only)
    # ---------------------------
    # Run this code path only when mode==inter; otherwise skip without returning early.
    if str(getattr(args, "mode", "")).lower() == "inter":
        paths.OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
        # 1) Build per-exchange universe of symbols with given QUOTE
        bases_ordered: List[str] = []
        symbols_per_ex: Dict[str, List[str]] = {}
        for ex_id in EX_IDS:
            try:
                ex = load_exchange(ex_id, args.timeout)
                if not safe_has(ex, "fetchTicker"):
                    if ex_id != "bitso":
                        logger.warning(
                            "%s: omitido (no soporta fetchTicker público)", ex_id
                        )
                    symbols_per_ex[ex_id] = []
                    continue
                markets = ex.load_markets()
                symbols: List[str] = []
                for s, m in markets.items():
                    if not m.get("active", True):
                        continue
                    if m.get("quote") == QUOTE:
                        sym, base = normalize_symbol(m)
                        symbols.append(sym)
                        if base not in bases_ordered:
                            bases_ordered.append(base)
                symbols_per_ex[ex_id] = symbols
                time.sleep(args.sleep)
            except ccxt.AuthenticationError:
                symbols_per_ex[ex_id] = []
                if ex_id != "bitso":
                    logger.warning("%s: omitido (requiere API key para datos)", ex_id)
            except Exception as e:
                symbols_per_ex[ex_id] = []
                logger.warning("%s: load_markets falló: %s", ex_id, e)

        bases_ordered = bases_ordered[:UNIVERSE_LIMIT]
        target_symbols = [f"{b}/{QUOTE}" for b in bases_ordered]

        current_file = paths.LOGS_DIR / "current_inter.txt"
        for it in range(1, int(max(1, args.repeat)) + 1):
            # Clean per-iteration artifacts
            try:
                if current_file.exists():
                    current_file.unlink()  # type: ignore[arg-type]
            except Exception:
                pass
            try:
                inter_hist = paths.LOGS_DIR / "inter_history.txt"
                if inter_hist.exists():
                    inter_hist.unlink()  # type: ignore[arg-type]
            except Exception:
                pass
            if args.console_clear:
                try:
                    if os.name == "nt":
                        os.system("cls")
                    else:
                        print("\033[2J\033[H", end="")
                except Exception:
                    pass

            # 2) Collect tickers
            rows = []
            for ex_id in EX_IDS:
                try:
                    ex = load_exchange(ex_id, args.timeout)
                    if not safe_has(ex, "fetchTicker"):
                        continue
                    have_batch = safe_has(ex, "fetchTickers")
                    use_batch = have_batch and args.ex.strip().lower() != "all"
                    start_ts = time.time()
                    items_checked = 0
                    if use_batch:
                        tickers = ex.fetch_tickers()
                        for sym in target_symbols:
                            if args.per_ex_limit and items_checked >= args.per_ex_limit:
                                break
                            if sym in tickers:
                                t = tickers[sym]
                                bid = t.get("bid")
                                ask = t.get("ask")
                                last = t.get("last")
                                if bid is None and last is not None:
                                    bid = last
                                if ask is None and last is not None:
                                    ask = last
                                if bid is None or ask is None or bid <= 0 or ask <= 0:
                                    continue
                                qvol = get_quote_volume(t)
                                rows.append(
                                    {
                                        "exchange": ex_id,
                                        "symbol": sym,
                                        "base": sym.split("/")[0],
                                        "bid": float(bid),
                                        "ask": float(ask),
                                        "qvol": qvol,
                                    }
                                )
                                items_checked += 1
                            if time.time() - start_ts > args.per_ex_timeout:
                                break
                        time.sleep(args.sleep)
                    else:
                        for sym in target_symbols:
                            if args.per_ex_limit and items_checked >= args.per_ex_limit:
                                break
                            if sym not in symbols_per_ex.get(ex_id, []):
                                continue
                            try:
                                t = ex.fetch_ticker(sym)
                                bid = t.get("bid") or t.get("last")
                                ask = t.get("ask") or t.get("last")
                                if not bid or not ask or bid <= 0 or ask <= 0:
                                    continue
                                qvol = get_quote_volume(t)
                                rows.append(
                                    {
                                        "exchange": ex_id,
                                        "symbol": sym,
                                        "base": sym.split("/")[0],
                                        "bid": float(bid),
                                        "ask": float(ask),
                                        "qvol": qvol,
                                    }
                                )
                                items_checked += 1
                                time.sleep(args.sleep)
                                if time.time() - start_ts > args.per_ex_timeout:
                                    break
                            except Exception:
                                continue
                except Exception as e:
                    logger.warning("%s: fetch tickers falló: %s", ex_id, e)

            df = pd.DataFrame(rows)
            if df.empty:
                logger.info("SIN_DATOS_VALIDOS")
                if it < args.repeat:
                    time.sleep(max(0.0, args.repeat_sleep))
                    continue
                return

            # 3) Best ask/bid per symbol with filters
            out_rows = []
            for sym, g in df.groupby("symbol"):
                if len(g) < args.min_sources:
                    continue
                buy_idx = g["ask"].idxmin()
                sell_idx = g["bid"].idxmax()
                if pd.isna(buy_idx) or pd.isna(sell_idx):
                    continue
                buy_row = g.loc[buy_idx]
                sell_row = g.loc[sell_idx]
                if sell_row["bid"] <= 0 or buy_row["ask"] <= 0:
                    continue
                base_token = str(buy_row["base"]).upper()
                if not args.include_stables and base_token in STABLE_BASES:
                    continue
                if args.min_price > 0.0 and (
                    buy_row["ask"] < args.min_price or sell_row["bid"] < args.min_price
                ):
                    continue

            def vol_ok(row) -> bool:
                if args.min_quote_vol <= 0:
                    return True
                qv = row.get("qvol", None)
                if qv is None:
                    return False if args.vol_strict else True
                return qv >= args.min_quote_vol

            if not (vol_ok(buy_row) and vol_ok(sell_row)):
                continue

            gross = pct(sell_row["bid"], buy_row["ask"])  # %
            if math.isnan(gross):
                continue
            if args.max_spread_cap and gross > args.max_spread_cap:
                continue
            est_net = gross - (args.buy_fee + args.sell_fee) - args.xfer_fee_pct
            inv_amt = float(args.inv)
            gross_profit_amt = round(inv_amt * (gross / 100.0), 2)
            net_profit_amt = round(inv_amt * (est_net / 100.0), 2)
            if gross >= args.min_spread:
                out_rows.append(
                    {
                        "symbol": sym,
                        "base": buy_row["base"],
                        "buy_exchange": buy_row["exchange"],
                        "buy_price": round(float(buy_row["ask"]), 8),
                        "sell_exchange": sell_row["exchange"],
                        "sell_price": round(float(sell_row["bid"]), 8),
                        "gross_spread_pct": round(gross, 4),
                        "est_net_pct": round(est_net, 4),
                        "sources": f"{len(g)}ex",
                        "gross_profit_amt": gross_profit_amt,
                        "net_profit_amt": net_profit_amt,
                    }
                )

            report = pd.DataFrame(out_rows)
            had_symbols = set(df["symbol"].unique())
            opp_symbols = set(report["symbol"].unique()) if not report.empty else set()
            no_opp_symbols = sorted(had_symbols - opp_symbols)

            if not report.empty:
                report.sort_values(
                    ["est_net_pct", "gross_spread_pct"],
                    ascending=[False, False],
                    inplace=True,
                )

                csv_opp = (
                    paths.OUTPUTS_DIR / f"arbitrage_report_{QUOTE.lower()}_ccxt.csv"
                )
                csv_no = (
                    paths.OUTPUTS_DIR
                    / f"arbitrage_report_{QUOTE.lower()}_ccxt_noop.csv"
                )
                if not report.empty:
                    report.to_csv(csv_opp, index=False)
                else:
                    pd.DataFrame(
                        columns=[
                            "symbol",
                            "base",
                            "buy_exchange",
                            "buy_price",
                            "sell_exchange",
                            "sell_price",
                            "gross_spread_pct",
                            "est_net_pct",
                            "sources",
                            "gross_profit_amt",
                            "net_profit_amt",
                        ]
                    ).to_csv(csv_opp, index=False)
                pd.DataFrame({"symbol": no_opp_symbols}).to_csv(csv_no, index=False)

                logger.info("== ARBITRAGE_REPORT_CCXT ==")
                logger.info(
                    "Oportunidades: %d | Sin oportunidad: %d | Total símbolos: %d",
                    0 if report.empty else len(report),
                    len(no_opp_symbols),
                    len(had_symbols),
                )
                lines: List[str] = []
                disclaimer = (
                    " [nota: datos multi-exchange; puede incluir venues no confiables o ilíquidos]"
                    if args.ex.strip().lower() == "all"
                    else ""
                )
                for _, r in report.head(args.top).iterrows():
                    buy_p = fmt_price(float(r["buy_price"]))
                    sell_p = fmt_price(float(r["sell_price"]))
                    lines.append(
                        f"{r['symbol']} => BUY@{r['buy_exchange']} {buy_p} → "
                        f"SELL@{r['sell_exchange']} {sell_p} "
                        f"(gross {r['gross_spread_pct']:.3f}% | net {r['est_net_pct']:.3f}%)"
                        + disclaimer
                    )
                if lines:
                    logger.info("\n" + "\n".join(lines))
                logger.info(
                    "\n%s",
                    tabulate(
                        report.head(args.top),
                        headers="keys",
                        tablefmt="github",
                        showindex=False,
                    ),
                )
                logger.info("CSV: %s", csv_opp)
                logger.info(
                    "Params: quote=%s max=%d min_spread=%s%% fees(buy/sell)=%s%%/%s%% xfer=%s%% exchanges=%s",
                    QUOTE,
                    UNIVERSE_LIMIT,
                    args.min_spread,
                    args.buy_fee,
                    args.sell_fee,
                    args.xfer_fee_pct,
                    ",".join(EX_IDS),
                )
            try:
                now_ts = pd.Timestamp.utcnow().isoformat()
                # Snapshot file (last iteration only)
                with open(current_file, "w", encoding="utf-8") as fh:
                    fh.write(f"[INTER] Iteración {it}/{args.repeat} @ {now_ts}\n")
                    if lines:
                        fh.write("\n".join(lines) + "\n")
                    else:
                        fh.write("(sin oportunidades en esta iteración)\n")
                # History file (overwrite per iteration)
                inter_hist = paths.LOGS_DIR / "inter_history.txt"
                with open(inter_hist, "w", encoding="utf-8") as fh:
                    fh.write(f"[INTER] Iteración {it}/{args.repeat} @ {now_ts}\n")
                    if lines:
                        fh.write("\n".join(lines) + "\n\n")
                    else:
                        fh.write("(sin oportunidades en esta iteración)\n\n")
            except Exception:
                pass
            if it < args.repeat:
                time.sleep(max(0.0, args.repeat_sleep))


# Ejecuta main() si el archivo es ejecutado como script
if __name__ == "__main__":
    main()
