from __future__ import annotations

import os
import sys
import time
import logging
from typing import Dict, List, Optional, Tuple
import re
from datetime import datetime, timedelta, timezone
import csv
from concurrent.futures import ThreadPoolExecutor, as_completed

import ccxt  # type: ignore
import yaml
import pandas as pd
from dotenv import load_dotenv, find_dotenv
try:
    from tabulate import tabulate  # type: ignore
except Exception:
    tabulate = None  # type: ignore


# -----------------------------
# Logging setup
# -----------------------------
logger = logging.getLogger("scalpin")
if not logger.handlers:
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    logger.addHandler(sh)


# -----------------------------
# Helpers
# -----------------------------
def env_get_stripped(name: str) -> Optional[str]:
    try:
        v = os.environ.get(name)
        if v is None:
            return None
        return v.strip()
    except Exception:
        return os.environ.get(name)


def normalize_ccxt_id(ex_id: str) -> str:
    x = (ex_id or "").strip().lower()
    aliases = {
        "gateio": "gate",
        "okex": "okx",
        "coinbasepro": "coinbase",
        "huobipro": "htx",
    }
    return aliases.get(x, x)


def build_symbol(base: str, quote: str) -> str:
    return f"{base.upper()}/{quote.upper()}"


def parse_yaml(path: str) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return yaml.safe_load(fh) or {}
    except FileNotFoundError:
        logger.warning("Config not found: %s (using defaults)", path)
        return {}
    except Exception as e:
        logger.warning("Failed to read YAML %s: %s (using defaults)", path, e)
        return {}


# -----------------------------
# ExchangeClient
# -----------------------------
class ExchangeClient:
    """Thin wrapper around ccxt to fetch balances and convert to a given anchor."""

    def __init__(self, ex_id: str, anchor: str, timeout_ms: int = 10000) -> None:
        self.ex_id = normalize_ccxt_id(ex_id)
        self.anchor = anchor.upper()
        self.timeout_ms = int(timeout_ms)
        self._ex = self._load_exchange()
        self._markets_loaded = False

    def _load_exchange(self):
        cls = getattr(ccxt, self.ex_id)
        cfg = {"enableRateLimit": True}
        creds = self._creds_from_env()
        if creds:
            cfg.update(creds)
        ex = cls(cfg)
        try:
            ex.timeout = self.timeout_ms
        except Exception:
            pass
        return ex

    def _creds_from_env(self) -> dict:
        ex = self.ex_id
        try:
            if ex == "binance":
                k = env_get_stripped("BINANCE_API_KEY"); s = env_get_stripped("BINANCE_API_SECRET")
                if k and s:
                    return {"apiKey": k, "secret": s}
            elif ex == "bybit":
                k = env_get_stripped("BYBIT_API_KEY"); s = env_get_stripped("BYBIT_API_SECRET")
                if k and s:
                    return {"apiKey": k, "secret": s}
            elif ex == "bitget":
                k = env_get_stripped("BITGET_API_KEY"); s = env_get_stripped("BITGET_API_SECRET"); p = env_get_stripped("BITGET_PASSWORD")
                if k and s and p:
                    return {"apiKey": k, "secret": s, "password": p}
            elif ex == "coinbase":
                k = env_get_stripped("COINBASE_API_KEY"); s = env_get_stripped("COINBASE_API_SECRET"); p = env_get_stripped("COINBASE_API_PASSWORD")
                if k and s and p:
                    return {"apiKey": k, "secret": s, "password": p}
            elif ex == "okx":
                k = env_get_stripped("OKX_API_KEY"); s = env_get_stripped("OKX_API_SECRET")
                p = env_get_stripped("OKX_API_PASSWORD") or env_get_stripped("OKX_PASSWORD")
                if k and s and p:
                    return {"apiKey": k, "secret": s, "password": p}
            elif ex == "gate":
                k = env_get_stripped("GATEIO_API_KEY") or env_get_stripped("GATE_API_KEY")
                s = env_get_stripped("GATEIO_API_SECRET") or env_get_stripped("GATE_API_SECRET")
                if k and s:
                    return {"apiKey": k, "secret": s}
            elif ex == "kucoin":
                k = env_get_stripped("KUCOIN_API_KEY"); s = env_get_stripped("KUCOIN_API_SECRET"); p = env_get_stripped("KUCOIN_API_PASSWORD")
                if k and s and p:
                    return {"apiKey": k, "secret": s, "password": p}
            elif ex == "mexc":
                k = env_get_stripped("MEXC_API_KEY"); s = env_get_stripped("MEXC_API_SECRET")
                if k and s:
                    return {"apiKey": k, "secret": s}
        except Exception:
            pass
        return {}

    def load_markets(self) -> dict:
        if not self._markets_loaded:
            try:
                self._ex.load_markets()
                self._markets_loaded = True
            except Exception as e:
                logger.warning("%s: load_markets failed: %s", self.ex_id, e)
        return getattr(self._ex, "markets", {}) or {}

    def fetch_balances(self) -> Dict[str, float]:
        """Return total balances per asset; exclude zero/None."""
        try:
            bal = self._ex.fetch_balance() or {}
            # Prefer free balances to avoid counting locked-in-order funds; fallback to total
            bucket = bal.get("free") or bal.get("total") or {}
            out: Dict[str, float] = {}
            if isinstance(bucket, dict):
                for ccy, amt in bucket.items():
                    try:
                        val = float(amt or 0.0)
                    except Exception:
                        val = 0.0
                    if val and abs(val) > 0.0:
                        out[str(ccy).upper()] = val
            return out
        except Exception as e:
            logger.warning("%s: fetch_balance failed: %s", self.ex_id, e)
            return {}

    def get_market_limits(self, base: str, quote: str) -> Tuple[Optional[float], Optional[float], Optional[str]]:
        """Return (min_cost, min_amount, symbol_orientation) for the market between base and quote if present.
        - min_cost is the minimum notional (quote currency) if available
        - min_amount is the minimum amount (base currency) if available
        - symbol_orientation is either 'base/quote', 'quote/base' or None if not found
        """
        try:
            markets = self.load_markets()
            b = base.upper(); q = quote.upper()
            s1 = f"{b}/{q}"; s2 = f"{q}/{b}"
            m1 = markets.get(s1)
            if isinstance(m1, dict):
                limits = m1.get("limits") or {}
                min_cost = None
                min_amount = None
                try:
                    lc = (limits.get("cost") or {}).get("min")
                    if lc is not None:
                        min_cost = float(lc)
                except Exception:
                    min_cost = None
                try:
                    la = (limits.get("amount") or {}).get("min")
                    if la is not None:
                        min_amount = float(la)
                except Exception:
                    min_amount = None
                return min_cost, min_amount, s1
            m2 = markets.get(s2)
            if isinstance(m2, dict):
                limits = m2.get("limits") or {}
                min_cost = None
                min_amount = None
                try:
                    lc = (limits.get("cost") or {}).get("min")
                    if lc is not None:
                        min_cost = float(lc)
                except Exception:
                    min_cost = None
                try:
                    la = (limits.get("amount") or {}).get("min")
                    if la is not None:
                        min_amount = float(la)
                except Exception:
                    min_amount = None
                return min_cost, min_amount, s2
        except Exception:
            pass
        return None, None, None

    def _rate_to_anchor(self, base: str, markets: dict, tickers: dict) -> Optional[float]:
        base = base.upper()
        if base == self.anchor:
            return 1.0
        s1 = build_symbol(base, self.anchor)
        s2 = build_symbol(self.anchor, base)
        # Prefer bid/ask; fallback to last
        t1 = tickers.get(s1) if s1 in tickers else None
        t2 = tickers.get(s2) if s2 in tickers else None
        if not t1 and not t2:
            # If we didn't fetch batch, try per-symbol
            try:
                if s1 in markets:
                    t1 = self._ex.fetch_ticker(s1)
                elif s2 in markets:
                    t2 = self._ex.fetch_ticker(s2)
            except Exception:
                t1 = t1 or None
                t2 = t2 or None
        if isinstance(t1, dict):
            bid = t1.get("bid") or t1.get("last")
            if bid and float(bid) > 0:
                return float(bid)
        if isinstance(t2, dict):
            ask = t2.get("ask") or t2.get("last")
            if ask and float(ask) > 0:
                return 1.0 / float(ask)
        # Try 1-hop bridge via USDT when direct market to anchor is not present
        bridge = "USDT"
        if base != bridge and self.anchor != bridge:
            # base -> bridge
            s_bb = build_symbol(base, bridge)
            s_bb_inv = build_symbol(bridge, base)
            tb = tickers.get(s_bb) if s_bb in tickers else None
            if not tb:
                tb = tickers.get(s_bb_inv) if s_bb_inv in tickers else None
            if not tb:
                try:
                    if s_bb in markets:
                        tb = self._ex.fetch_ticker(s_bb)
                    elif s_bb_inv in markets:
                        tb = self._ex.fetch_ticker(s_bb_inv)
                except Exception:
                    tb = None
            rate_bb: Optional[float] = None
            if isinstance(tb, dict):
                if s_bb in markets and tb:
                    rate_bb = float(tb.get("bid") or tb.get("last") or 0) or None
                elif s_bb_inv in markets and tb:
                    val = float(tb.get("ask") or tb.get("last") or 0)
                    rate_bb = (1.0 / val) if val else None
            # bridge -> anchor
            s_ba = build_symbol(bridge, self.anchor)
            s_ba_inv = build_symbol(self.anchor, bridge)
            ta = tickers.get(s_ba) if s_ba in tickers else None
            if not ta:
                ta = tickers.get(s_ba_inv) if s_ba_inv in tickers else None
            if not ta:
                try:
                    if s_ba in markets:
                        ta = self._ex.fetch_ticker(s_ba)
                    elif s_ba_inv in markets:
                        ta = self._ex.fetch_ticker(s_ba_inv)
                except Exception:
                    ta = None
            rate_ba: Optional[float] = None
            if isinstance(ta, dict):
                if s_ba in markets and ta:
                    rate_ba = float(ta.get("bid") or ta.get("last") or 0) or None
                elif s_ba_inv in markets and ta:
                    val = float(ta.get("ask") or ta.get("last") or 0)
                    rate_ba = (1.0 / val) if val else None
            if rate_bb and rate_ba:
                try:
                    return float(rate_bb) * float(rate_ba)
                except Exception:
                    return None
        return None

    def fetch_prices_in_anchor(self, assets: List[str]) -> Dict[str, float]:
        assets_u = [a.upper() for a in assets]
        markets = self.load_markets()
        # Build needed symbols
        symbols = set()
        for a in assets_u:
            if a == self.anchor:
                continue
            s1 = build_symbol(a, self.anchor)
            s2 = build_symbol(self.anchor, a)
            if s1 in markets:
                symbols.add(s1)
            if s2 in markets:
                symbols.add(s2)
            # Add bridge pairs via USDT to improve coverage
            bridge = "USDT"
            if a != bridge and self.anchor != bridge:
                s_bb = build_symbol(a, bridge)
                s_bb_inv = build_symbol(bridge, a)
                s_ba = build_symbol(bridge, self.anchor)
                s_ba_inv = build_symbol(self.anchor, bridge)
                for s in (s_bb, s_bb_inv, s_ba, s_ba_inv):
                    if s in markets:
                        symbols.add(s)
        # Fetch batch when supported
        tickers: Dict[str, dict] = {}
        try:
            have_batch = bool(self._ex.has.get("fetchTickers"))
        except Exception:
            have_batch = False
        if have_batch and symbols:
            try:
                tick_all = self._ex.fetch_tickers(list(symbols))  # type: ignore[arg-type]
                if isinstance(tick_all, dict):
                    for s in symbols:
                        t = tick_all.get(s)
                        if isinstance(t, dict):
                            tickers[s] = t
            except Exception:
                pass
        # Build prices
        prices: Dict[str, float] = {}
        for a in assets_u:
            r = self._rate_to_anchor(a, markets, tickers) if a != self.anchor else 1.0
            if r is not None and r > 0:
                prices[a] = float(r)
        return prices


# -----------------------------
# ScalpinMonitor
# -----------------------------
class ScalpinMonitor:
    def __init__(self, config_path: str = "scalpin.yaml") -> None:
        # Load .env at startup from multiple candidate locations and keep track of what was loaded
        self._loaded_env_files: List[str] = []
        try:
            primary = find_dotenv(usecwd=True)
            if primary:
                load_dotenv(dotenv_path=primary, override=False)
                self._loaded_env_files.append(os.path.abspath(primary))
        except Exception:
            try:
                load_dotenv(override=False)
            except Exception:
                pass
        try:
            cwd = os.getcwd()
            candidates = []
            # Parent of CWD
            candidates.append(os.path.join(os.path.dirname(cwd), ".env"))
            # Directory of config file
            if config_path:
                candidates.append(os.path.join(os.path.dirname(os.path.abspath(config_path)), ".env"))
            # Directory of this script file
            candidates.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))
            # Load any existing candidates without overriding earlier values
            for p in candidates:
                try:
                    if p and os.path.exists(p):
                        ap = os.path.abspath(p)
                        if ap not in self._loaded_env_files:
                            load_dotenv(dotenv_path=p, override=False)
                            self._loaded_env_files.append(ap)
                except Exception:
                    pass
        except Exception:
            pass
        self.cfg = parse_yaml(config_path)
        # Resolve config path/dir and base artifacts dir (defaults anchored to config directory)
        self.config_path = os.path.abspath(config_path)
        self.config_dir = os.path.dirname(self.config_path)
        self.base_artifacts_dir = str(self.cfg.get("base_artifacts_dir") or os.path.join(self.config_dir, "artifacts"))
        self.exchanges: List[str] = [normalize_ccxt_id(x) for x in (self.cfg.get("exchanges") or [])]
        self.assets_validos: List[str] = [a.upper() for a in (self.cfg.get("assets_validos") or [])]
        self.anchor: str = str(self.cfg.get("anchor") or "USDT").upper()
        self.poll_sec: float = float(self.cfg.get("poll_interval_sec") or 1)
        self.min_value_anchor: float = float(self.cfg.get("min_value_anchor") or 0.0)
        # Optional duration controls
        self.run_duration_sec: float = float(self.cfg.get("run_duration_sec") or 0.0)
        # Default to 1000 iterations when not specified
        self.max_iterations: int = int(self.cfg.get("max_iterations") or 1000)
        # Profit action threshold in percent (e.g. 0.05 means 0.05%)
        self.profit_action_threshold_pct: float = float(self.cfg.get("profit_action_threshold_pct") or 0.05)
        timeout_ms = int(self.cfg.get("timeout_ms") or 10000)
        # Output snapshot path (overwritten every tick)
        default_out = os.path.join(self.base_artifacts_dir, "scalpin", "current_scalpin.csv")
        self.output_csv: str = str(self.cfg.get("output_csv") or default_out)
        # Output text log snapshot (overwritten every tick)
        default_log = os.path.join(self.base_artifacts_dir, "scalpin", "current_scalpin.log")
        self.output_log: str = str(self.cfg.get("output_log") or default_log)
        # Persistent history logs (append-only)
        default_hist_log = os.path.join(self.base_artifacts_dir, "scalpin", "scalpin_history.log")
        default_hist_csv = os.path.join(self.base_artifacts_dir, "scalpin", "scalpin_history.csv")
        self.history_log_enabled = bool(self.cfg.get("history_log_enabled", True))
        self.history_log_path = str(self.cfg.get("history_log_path") or default_hist_log)
        self.history_csv_path = str(self.cfg.get("history_csv_path") or default_hist_csv)
        # Table format for console/log rendering (requires tabulate)
        self.table_format = str(self.cfg.get("table_format") or "grid")
        # Performance controls
        self.fast_mode = bool(self.cfg.get("fast_mode", False))  # avoid pandas for render/csv
        self.concurrency = int(self.cfg.get("concurrency") or max(1, len(self.exchanges)))
        # Frequency controls (production-friendly)
        self.snapshot_every_n = int(self.cfg.get("snapshot_every_n") or 1)
        self.log_every_n = int(self.cfg.get("log_every_n") or 5)
        self.history_every_n = int(self.cfg.get("history_every_n") or 10)
        self.render_every_n = int(self.cfg.get("render_every_n") or 5)
        # Build clients
        self.clients = {ex: ExchangeClient(ex, anchor=self.anchor, timeout_ms=timeout_ms) for ex in self.exchanges}
        self.iteration = 0
        # Track last seen price per (exchange, asset) to compute tick-over-tick change
        self._last_price = {}
        # Console refresh behavior
        self.clear_screen = bool(self.cfg.get("clear_screen", True))
        # Performance metrics
        self._perf_hist = []
        self.perf_window = int(self.cfg.get("perf_window") or 50)
        default_perf_csv = os.path.join(self.base_artifacts_dir, "scalpin", "scalpin_perf.csv")
        self.perf_csv_path = str(self.cfg.get("perf_csv_path") or default_perf_csv)
        self.perf_csv_enabled = bool(self.cfg.get("perf_csv_enabled", True))
        # Swapper log path (configurable), defaults anchored to config dir
        default_swapper_log = os.path.join(self.base_artifacts_dir, "arbitraje", "logs", "swapper.log")
        self.swapper_log_path: str = str(self.cfg.get("swapper_log_path") or default_swapper_log)
        # Recalibration knobs
        try:
            self.min_amount_multiplier: float = float(self.cfg.get("min_amount_multiplier") or 1.2)
        except Exception:
            self.min_amount_multiplier = 1.2
        try:
            self.mirror_cooldown_minutes: float = float(self.cfg.get("mirror_cooldown_minutes") or 12)
        except Exception:
            self.mirror_cooldown_minutes = 12.0
        # Optional: read swapper config for fallback min_notional and sizing defaults
        try:
            repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
            swap_cfg_path = os.path.join(repo_root, "projects", "arbitraje", "swapper.live.yaml")
            scfg = parse_yaml(swap_cfg_path)
            self._fallback_min_notional = float(scfg.get("min_notional") or 0.0)
        except Exception:
            self._fallback_min_notional = 0.0
        # Initial balances snapshot (valor_anchor) captured on first render to compute accumulated profit in views
        self._initial_balances: Dict[tuple, float] = {}
        self._snapshot_taken: bool = False
        # Cache of mirror states parsed from swapper.log: {(exchange, start_ccy): (state, ts_iso, extra)}
        self._mirror_states: Dict[Tuple[str, str], Tuple[str, str, Dict[str, str]]] = {}
        # Log diagnostic info about loaded envs and config
        try:
            logger.info(
                "Config loaded | config=%s | base_artifacts=%s | loaded_envs=%s",
                self.config_path,
                self.base_artifacts_dir,
                ";".join(self._loaded_env_files) or "(none)",
            )
        except Exception:
            pass
        # Credential presence diagnostics
        try:
            for ex in self.exchanges:
                missing = self._missing_creds_vars(ex)
                if missing:
                    logger.warning("%s: missing credentials in environment: %s", ex, ",".join(missing))
        except Exception:
            pass

    def _missing_creds_vars(self, ex: str) -> List[str]:
        ex = normalize_ccxt_id(ex)
        required: List[str] = []
        if ex == "binance":
            required = ["BINANCE_API_KEY", "BINANCE_API_SECRET"]
        elif ex == "bybit":
            required = ["BYBIT_API_KEY", "BYBIT_API_SECRET"]
        elif ex == "bitget":
            required = ["BITGET_API_KEY", "BITGET_API_SECRET", "BITGET_PASSWORD"]
        elif ex == "coinbase":
            required = ["COINBASE_API_KEY", "COINBASE_API_SECRET", "COINBASE_API_PASSWORD"]
        elif ex == "okx":
            required = ["OKX_API_KEY", "OKX_API_SECRET", "OKX_API_PASSWORD"]
        elif ex == "gate":
            required = ["GATEIO_API_KEY", "GATEIO_API_SECRET"]
        elif ex == "kucoin":
            required = ["KUCOIN_API_KEY", "KUCOIN_API_SECRET", "KUCOIN_API_PASSWORD"]
        elif ex == "mexc":
            required = ["MEXC_API_KEY", "MEXC_API_SECRET"]
        missing = []
        for var in required:
            if not env_get_stripped(var):
                missing.append(var)
        return missing

    def _filter_assets(self, balances: Dict[str, float]) -> Dict[str, float]:
        if not self.assets_validos:
            return balances
        out: Dict[str, float] = {}
        allowed = set(self.assets_validos)
        for a, v in balances.items():
            if a.upper() in allowed:
                out[a] = v
        return out

    def _build_table_rows(self) -> List[dict]:
        rows: List[dict] = []
        now_utc = datetime.now(timezone.utc)

        # Parse latest mirror states once per tick for gating/visibility
        try:
            self._mirror_states = self._parse_mirror_states_from_log(self.swapper_log_path)
        except Exception:
            self._mirror_states = {}

        def worker(ex_id: str, client: ExchangeClient) -> List[dict]:
            local_rows: List[dict] = []
            balances = client.fetch_balances()
            if not balances:
                return local_rows
            balances = self._filter_assets(balances)
            assets = list(balances.keys())
            prices = client.fetch_prices_in_anchor(assets)
            for asset, bal in balances.items():
                price = prices.get(asset.upper())
                if price is None or price <= 0:
                    continue
                value_anchor = float(bal) * float(price)
                if self.min_value_anchor and value_anchor < self.min_value_anchor:
                    continue
                key = (ex_id, asset.upper())
                # Ensure initial snapshot is set for NEW assets as they appear, even after the first snapshot.
                # This keeps "balance inicial" populated for re-incorporated coins.
                if key not in self._initial_balances:
                    try:
                        self._initial_balances[key] = float(value_anchor)
                    except Exception:
                        self._initial_balances[key] = 0.0
                prev_px = self._last_price.get(key)
                if prev_px and prev_px > 0:
                    try:
                        profit_pct = (float(price) / float(prev_px) - 1.0) * 100.0
                    except Exception:
                        profit_pct = 0.0
                else:
                    profit_pct = 0.0
                self._last_price[key] = float(price)
                # Compute ProfitAcum (display-only) for trigger guard
                init_val = self._initial_balances.get(key)
                try:
                    profit_acum = (float(value_anchor) - float(init_val)) if init_val is not None else 0.0
                except Exception:
                    profit_acum = 0.0
                accion = ""
                mirror_status = ""
                if (
                    profit_pct is not None
                    and profit_pct > float(self.profit_action_threshold_pct)
                    ##and profit_acum > 0.0
                ):
                    # 1) Gate by mirror_pending status for this (exchange, asset)
                    mkey = (ex_id, asset.upper())
                    mstate = self._mirror_states.get(mkey)
                    if mstate:
                        # mstate: (state, ts_iso, extras)
                        last_state = mstate[0]
                        ts_iso = mstate[1] or ""
                        # Parse timestamp "YYYY-MM-DD HH:MM:SS,mmm"
                        age_min = None
                        try:
                            if ts_iso:
                                dt = datetime.strptime(ts_iso, "%Y-%m-%d %H:%M:%S,%f").replace(tzinfo=timezone.utc)
                                age_min = (now_utc - dt).total_seconds() / 60.0
                        except Exception:
                            # Fallback: if only date captured, treat as very old
                            age_min = None
                        if last_state == "mirror_pending":
                            mirror_status = "pending"
                            # Always pause when a mirror is currently pending
                            if age_min is not None:
                                accion = f"PAUSA (mirror pendiente, {age_min:.1f}m)"
                            else:
                                accion = "PAUSA (mirror pendiente)"
                        elif last_state in ("failed", "ok") and self.mirror_cooldown_minutes and age_min is not None and age_min < float(self.mirror_cooldown_minutes):
                            mirror_status = last_state
                            # Cooldown shortly after a close to avoid rapid re-triggers
                            remaining = float(self.mirror_cooldown_minutes) - float(age_min)
                            accion = f"PAUSA (cooldown {remaining:.1f}m)"
                    else:
                        # 2) Gate by min_notional/amount limits for first hop asset->anchor
                        min_cost, min_amount, sym_used = client.get_market_limits(asset.upper(), self.anchor)
                        # Compute available notional in quote using free balance and price
                        try:
                            avail_notional = float(bal) * float(price)
                        except Exception:
                            avail_notional = 0.0
                        below_min = False
                        reason = ""
                        if (min_cost is not None) and min_cost > 0:
                            if avail_notional + 1e-12 < float(min_cost):
                                below_min = True
                                reason = f"min_notional {float(min_cost):.6f} > avail {float(avail_notional):.6f}"
                        elif (min_amount is not None) and min_amount > 0:
                            # Dust guard: require balance >= min_amount * multiplier to absorb fees/precision
                            min_amt_req = float(min_amount) * float(self.min_amount_multiplier or 1.0)
                            if float(bal) + 1e-12 < float(min_amt_req):
                                below_min = True
                                reason = f"min_amount {float(min_amount):.8f}*{float(self.min_amount_multiplier):.2f} > bal {float(bal):.8f}"
                        else:
                            # Fallback to swapper config min_notional if available
                            if float(self._fallback_min_notional or 0.0) > 0 and avail_notional + 1e-12 < float(self._fallback_min_notional):
                                below_min = True
                                reason = f"fallback_min_notional {float(self._fallback_min_notional):.6f} > avail {float(avail_notional):.6f}"
                        if below_min:
                            accion = f"PAUSA (debajo mínimo: {reason})"
                        else:
                            accion = f"@{ex_id} swap {asset.upper()}->{self.anchor}->{asset.upper()}"
                            if accion:
                                # Spawn swapper
                                repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
                                cfg_path = os.path.join(repo_root, "projects", "arbitraje", "swapper.live.yaml")
                                swap_path = f"{asset.upper()}->{self.anchor}->{asset.upper()}"
                                cmd = [
                                    sys.executable,
                                    "-m",
                                    "arbitraje.swapper",
                                    "--config",
                                    cfg_path,
                                    "--exchange",
                                    ex_id,
                                    "--path",
                                    swap_path,
                                ]
                                logger.info(
                                    "Spawning swapper: exchange=%s path=%s config=%s", ex_id, swap_path, cfg_path
                                )
                                try:
                                    env_map = dict(os.environ)
                                    swapper_log = str(self.swapper_log_path or "").strip()
                                    if swapper_log:
                                        env_map["SWAPPER_LOG_FILE"] = swapper_log
                                    env_map["PYTHONPATH"] = os.path.join(repo_root, "projects", "arbitraje", "src")
                                    __import__("subprocess").Popen(
                                        cmd,
                                        env=env_map,
                                    )
                                except Exception as e:
                                    logger.error("Failed to spawn swapper: %s", e, exc_info=True)
                # If mirror status not set above, surface any last known mirror state for visibility
                if not mirror_status:
                    mstate = self._mirror_states.get((ex_id, asset.upper()))
                    mirror_status = (mstate[0] if mstate else "")
                local_rows.append(
                    {
                        "exchange": ex_id,
                        "asset": asset.upper(),
                        "anchor": self.anchor,
                        "valor_anchor": round(value_anchor, 8),
                        "profit_pct": round(profit_pct, 6),
                        "mirror": mirror_status,
                        "accion": accion,
                    }
                )
            return local_rows

        if self.concurrency > 1 and len(self.clients) > 1:
            with ThreadPoolExecutor(max_workers=self.concurrency) as pool:
                futures = {pool.submit(worker, ex_id, client): ex_id for ex_id, client in self.clients.items()}
                for fut in as_completed(futures):
                    try:
                        rows.extend(fut.result())
                    except Exception as e:
                        logger.warning("worker error: %s", e)
        else:
            for ex_id, client in self.clients.items():
                rows.extend(worker(ex_id, client))
        # Sort by valor_anchor desc
        rows.sort(key=lambda r: r.get("valor_anchor", 0.0), reverse=True)
        # Mark snapshot taken after first full pass if we captured any initial balances
        if not self._snapshot_taken and self._initial_balances:
            self._snapshot_taken = True
        return rows

    def _parse_mirror_states_from_log(self, log_path: str) -> Dict[Tuple[str, str], Tuple[str, str, Dict[str, str]]]:
        """Parse swapper.log and return latest mirror state per (exchange, start_ccy).

        Recognized states:
        - mirror_pending: result status indicates pending mirror
        - forced_close: a mirror_forced_close entry was recorded
        - reemit: mirror_reemit observed (treated as pending for gating)
        - ok/failed: final states; we clear gating on these

        Returns a mapping: {(exchange, start_ccy): (state, ts_iso, extras)}
        """
        out: Dict[Tuple[str, str], Tuple[str, str, Dict[str, str]]] = {}
        try:
            if not log_path or not os.path.exists(log_path):
                return out
            # Read last N lines to avoid huge files
            with open(log_path, "r", encoding="utf-8", errors="ignore") as fh:
                lines = fh.readlines()
            tail = lines[-2000:] if len(lines) > 2000 else lines
            # Regexes
            # Capture full timestamp, e.g., "2025-10-20 19:24:00,902"
            re_ts = re.compile(r"^(?P<ts>\d{4}-\d{2}-\d{2} [0-9:,]+)")
            re_result = re.compile(r"result \|[^\n]*status=(?P<status>[a-zA-Z_]+)[^\n]*exchange=(?P<ex>[a-z0-9_]+)[^\n]*amount_used=[^\n]*\s(?P<start>[A-Z0-9_]{3,10})\b")
            re_forced = re.compile(r"mirror_forced_close \|[^\n]*symbol=")
            re_reemit = re.compile(r"mirror_reemit \|")
            for raw in reversed(tail):
                line = raw.strip()
                if not line:
                    continue
                ts_m = re_ts.search(line)
                ts_iso = ts_m.group("ts") if ts_m else ""
                m = re_result.search(line)
                if m:
                    ex = normalize_ccxt_id(m.group("ex"))
                    start = m.group("start").upper()
                    status = m.group("status").lower()
                    key = (ex, start)
                    state = ""
                    if status == "mirror_pending":
                        state = "mirror_pending"
                    elif status == "ok":
                        state = "ok"
                    elif status == "failed":
                        state = "failed"
                    if state:
                        out[key] = (state, ts_iso, {})
                    # If we've collected states for all current exchanges/assets, we could early-exit; keep simple
                    continue
                # We keep reemit and forced close as global hints; without start_ccy we can't key precisely
                # But if only one asset/exchange is active, this can still be informative. Skip mapping to a key.
                # Optionally, could store under a special key.
                _ = re_forced.search(line) or re_reemit.search(line)
            return out
        except Exception:
            return {}

    def _render(self, rows: List[dict], print_console: bool = True) -> pd.DataFrame:
        self.iteration += 1
        if self.clear_screen and print_console:
            try:
                os.system("cls" if os.name == "nt" else "clear")
            except Exception:
                pass
        # Build header with elapsed time and timestamp
        now_utc = datetime.now(timezone.utc)
        if not hasattr(self, "_t0") or self._t0 is None:
            self._t0 = now_utc
        elapsed = now_utc - self._t0
        iter_total = self.max_iterations if self.max_iterations else "Γê₧"
        title = "SCALPIN - Saldos por exchange/asset"
        # Perf summary for last iteration if available
        perf = getattr(self, "_last_perf", None)
        perf_str = ""
        if isinstance(perf, dict):
            perf_str = (
                f" | lat(ms): rows={int(perf.get('ms_rows',0))} r={int(perf.get('row_count',0))}"
                f" render={int(perf.get('ms_render',0))} snap={int(perf.get('ms_snapshot',0))}"
                f" log={int(perf.get('ms_log',0))} hist={int(perf.get('ms_hist',0))} tot={int(perf.get('ms_total',0))}"
            )
        header = f"{title}\nanchor={self.anchor} | exchanges={','.join(self.exchanges)} | iter {self.iteration}/{iter_total} | elapsed={str(elapsed).split('.')[0]} | ts={now_utc.isoformat()}{perf_str}"
        if print_console:
            print("\n" + header + "\n")
        if not rows:
            if print_console:
                print("(sin saldos o por debajo de min_value_anchor)")
            return pd.DataFrame(columns=["exchange", "asset", "anchor", "valor_anchor", "profit_pct", "mirror", "accion", "ts"])
        try:
            df = pd.DataFrame(rows, columns=["exchange", "asset", "anchor", "valor_anchor", "profit_pct", "mirror", "accion"])
        except Exception:
            df = pd.DataFrame(rows)
        # Take initial snapshot on first render only
        if not self._snapshot_taken and not df.empty:
            try:
                for _, r in df.iterrows():
                    key = (str(r.get("exchange", "")), str(r.get("asset", "")))
                    try:
                        self._initial_balances[key] = float(r.get("valor_anchor", 0.0) or 0.0)
                    except Exception:
                        self._initial_balances[key] = 0.0
                self._snapshot_taken = True
            except Exception:
                pass
        # Pretty print
        if self.fast_mode:
            # Build rows directly to avoid DataFrame overhead with new columns
            cols = ["exchange", "asset", "anchor", "balance inicial", "balance actual", "ProfitAcum", "iter profit%", "mirror", "accion"]
            view_rows: List[Dict[str, str]] = []
            # running totals
            total_init = 0.0
            total_actual = 0.0
            total_profit = 0.0
            for r in rows:
                key = (str(r.get("exchange", "")), str(r.get("asset", "")))
                init_bal = self._initial_balances.get(key)
                try:
                    bal_actual = float(r.get("valor_anchor", 0.0) or 0.0)
                except Exception:
                    bal_actual = 0.0
                profit_acum = (bal_actual - float(init_bal)) if init_bal is not None else 0.0
                # accumulate totals
                try:
                    total_init += float(init_bal) if init_bal is not None else 0.0
                except Exception:
                    pass
                total_actual += float(bal_actual or 0.0)
                total_profit += float(profit_acum or 0.0)
                view_rows.append({
                    "exchange": r.get("exchange", ""),
                    "asset": r.get("asset", ""),
                    "anchor": r.get("anchor", ""),
                    "balance inicial": (f"{float(init_bal):.6f}" if init_bal is not None else ""),
                    "balance actual": f"{bal_actual:.6f}",
                    "ProfitAcum": f"{profit_acum:.6f}",
                    "iter profit%": f"{float(r.get('profit_pct', 0.0)):.4f}%",
                    "mirror": r.get("mirror", ""),
                    "accion": r.get("accion", ""),
                })
            # Append totals row
            if view_rows:
                view_rows.append({
                    "exchange": "",
                    "asset": "TOTAL",
                    "anchor": self.anchor,
                    "balance inicial": f"{total_init:.6f}",
                    "balance actual": f"{total_actual:.6f}",
                    "ProfitAcum": f"{total_profit:.6f}",
                    "iter profit%": "",
                    "mirror": "",
                    "accion": "",
                })
            if print_console:
                print(self._format_table(pd.DataFrame(view_rows), cols))
        else:
            df_view = df.copy()
            # Compute display-only columns: initial balance, current balance, accumulated profit, and iteration profit%
            def _init_bal(row):
                return self._initial_balances.get((str(row.get("exchange")), str(row.get("asset"))))
            try:
                df_view["balance inicial"] = df_view.apply(_init_bal, axis=1)
            except Exception:
                df_view["balance inicial"] = None
            try:
                df_view["balance actual"] = df_view["valor_anchor"].astype(float)
            except Exception:
                df_view["balance actual"] = df_view["valor_anchor"]
            try:
                df_view["ProfitAcum"] = (df_view["balance actual"].astype(float) - df_view["balance inicial"].astype(float))
            except Exception:
                try:
                    df_view["ProfitAcum"] = df_view["balance actual"].astype(float) - df_view["balance inicial"].fillna(0.0).astype(float)
                except Exception:
                    df_view["ProfitAcum"] = 0.0
            try:
                df_view["iter profit%"] = df_view["profit_pct"].apply(lambda x: f"{float(x):.4f}%")
            except Exception:
                df_view["iter profit%"] = df_view.get("profit_pct", [])
            # Append totals row for display
            try:
                if not df_view.empty:
                    tot_init = float(pd.to_numeric(df_view["balance inicial"], errors="coerce").fillna(0.0).sum()) if "balance inicial" in df_view.columns else 0.0
                    tot_actual = float(pd.to_numeric(df_view["balance actual"], errors="coerce").fillna(0.0).sum()) if "balance actual" in df_view.columns else 0.0
                    tot_profit = float(pd.to_numeric(df_view["ProfitAcum"], errors="coerce").fillna(0.0).sum()) if "ProfitAcum" in df_view.columns else 0.0
                    total_row = {
                        "exchange": "",
                        "asset": "TOTAL",
                        "anchor": self.anchor,
                        "balance inicial": f"{tot_init:.6f}",
                        "balance actual": f"{tot_actual:.6f}",
                        "ProfitAcum": f"{tot_profit:.6f}",
                        "iter profit%": "",
                        "accion": "",
                    }
                    df_view = pd.concat([df_view, pd.DataFrame([total_row])], ignore_index=True)
            except Exception:
                pass
            cols = ["exchange", "asset", "anchor", "balance inicial", "balance actual", "ProfitAcum", "iter profit%", "mirror", "accion"]
            cols = [c for c in cols if c in df_view.columns]
            if print_console:
                print(self._format_table(df_view, cols))
        return df

    def _write_snapshot(self, rows: List[dict]) -> None:
        """Write current snapshot to CSV, overwriting previous content."""
        try:
            out_dir = os.path.dirname(self.output_csv)
            if out_dir and not os.path.isdir(out_dir):
                os.makedirs(out_dir, exist_ok=True)
            tmp_path = self.output_csv + ".tmp"
            if self.fast_mode:
                cols = ["exchange", "asset", "anchor", "valor_anchor", "profit_pct", "mirror", "accion"]
                with open(tmp_path, "w", newline="", encoding="utf-8") as fh:
                    writer = csv.DictWriter(fh, fieldnames=cols)
                    writer.writeheader()
                    for r in rows:
                        writer.writerow({k: r.get(k, "") for k in cols})
                    fh.flush()
                    try:
                        os.fsync(fh.fileno())
                    except Exception:
                        pass
            else:
                df = pd.DataFrame(rows, columns=["exchange", "asset", "anchor", "valor_anchor", "profit_pct", "mirror", "accion"]) if rows else pd.DataFrame(columns=["exchange", "asset", "anchor", "valor_anchor", "profit_pct", "mirror", "accion"])            
                df.to_csv(tmp_path, index=False)
            try:
                os.replace(tmp_path, self.output_csv)
            except Exception:
                try:
                    # Fallback: write directly
                    if self.fast_mode:
                        cols = ["exchange", "asset", "anchor", "valor_anchor", "profit_pct", "mirror", "accion"]
                        with open(self.output_csv, "w", newline="", encoding="utf-8") as fh:
                            writer = csv.DictWriter(fh, fieldnames=cols)
                            writer.writeheader()
                            for r in rows:
                                writer.writerow({k: r.get(k, "") for k in cols})
                            fh.flush()
                            try:
                                os.fsync(fh.fileno())
                            except Exception:
                                pass
                    else:
                        df = pd.DataFrame(rows, columns=["exchange", "asset", "anchor", "valor_anchor", "profit_pct", "mirror", "accion"]) if rows else pd.DataFrame(columns=["exchange", "asset", "anchor", "valor_anchor", "profit_pct", "mirror", "accion"])            
                        df.to_csv(self.output_csv, index=False)
                finally:
                    try:
                        if os.path.exists(tmp_path):
                            os.remove(tmp_path)
                    except Exception:
                        pass
        except Exception as e:
            logger.warning("Failed to write snapshot CSV %s: %s", self.output_csv, e)

    def _write_log_snapshot(self, df: pd.DataFrame) -> None:
        """Write current table as text to a log file, overwriting each tick."""
        try:
            out_dir = os.path.dirname(self.output_log)
            if out_dir and not os.path.isdir(out_dir):
                os.makedirs(out_dir, exist_ok=True)
            title = "SCALPIN - Saldos por exchange/asset"
            now_utc = datetime.now(timezone.utc)
            if not hasattr(self, "_t0") or self._t0 is None:
                self._t0 = now_utc
            elapsed = now_utc - self._t0
            iter_total = self.max_iterations if self.max_iterations else "Γê₧"
            header = f"{title}\nanchor={self.anchor} | exchanges={','.join(self.exchanges)} | iter {self.iteration}/{iter_total} | elapsed={str(elapsed).split('.')[0]} | ts={now_utc.isoformat()}"
            # Build display with initial balance and accumulated profit columns for the log snapshot
            disp_cols = ["exchange", "asset", "anchor", "balance inicial", "balance actual", "ProfitAcum", "iter profit%", "mirror", "accion"]
            if self.fast_mode:
                view_rows: List[Dict[str, str]] = []
                total_init = 0.0
                total_actual = 0.0
                total_profit = 0.0
                for r in df.to_dict(orient="records"):
                    key = (str(r.get("exchange", "")), str(r.get("asset", "")))
                    init_bal = self._initial_balances.get(key)
                    try:
                        bal_actual = float(r.get("valor_anchor", 0.0) or 0.0)
                    except Exception:
                        bal_actual = 0.0
                    profit_acum = (bal_actual - float(init_bal)) if init_bal is not None else 0.0
                    try:
                        total_init += float(init_bal) if init_bal is not None else 0.0
                    except Exception:
                        pass
                    total_actual += float(bal_actual or 0.0)
                    total_profit += float(profit_acum or 0.0)
                    view_rows.append({
                        "exchange": r.get("exchange", ""),
                        "asset": r.get("asset", ""),
                        "anchor": r.get("anchor", ""),
                        "balance inicial": (f"{float(init_bal):.6f}" if init_bal is not None else ""),
                        "balance actual": f"{bal_actual:.6f}",
                        "ProfitAcum": f"{profit_acum:.6f}",
                        "iter profit%": f"{float(r.get('profit_pct', 0.0)):.4f}%",
                        "mirror": r.get("mirror", ""),
                        "accion": r.get("accion", ""),
                    })
                if view_rows:
                    view_rows.append({
                        "exchange": "",
                        "asset": "TOTAL",
                        "anchor": self.anchor,
                        "balance inicial": f"{total_init:.6f}",
                        "balance actual": f"{total_actual:.6f}",
                        "ProfitAcum": f"{total_profit:.6f}",
                        "iter profit%": "",
                        "accion": "",
                    })
                text = header + "\n" + self._format_table(pd.DataFrame(view_rows), disp_cols)
            else:
                df_view = df.copy()
                def _init_bal_r(row):
                    return self._initial_balances.get((str(row.get("exchange")), str(row.get("asset"))))
                try:
                    df_view["balance inicial"] = df_view.apply(_init_bal_r, axis=1)
                except Exception:
                    df_view["balance inicial"] = None
                try:
                    df_view["balance actual"] = df_view["valor_anchor"].astype(float)
                except Exception:
                    df_view["balance actual"] = df_view["valor_anchor"]
                try:
                    df_view["ProfitAcum"] = (df_view["balance actual"].astype(float) - df_view["balance inicial"].astype(float))
                except Exception:
                    try:
                        df_view["ProfitAcum"] = df_view["balance actual"].astype(float) - df_view["balance inicial"].fillna(0.0).astype(float)
                    except Exception:
                        df_view["ProfitAcum"] = 0.0
                try:
                    df_view["iter profit%"] = df_view["profit_pct"].apply(lambda x: f"{float(x):.4f}%")
                except Exception:
                    df_view["iter profit%"] = df_view.get("profit_pct", [])
                # Append totals row
                try:
                    if not df_view.empty:
                        tot_init = float(pd.to_numeric(df_view["balance inicial"], errors="coerce").fillna(0.0).sum()) if "balance inicial" in df_view.columns else 0.0
                        tot_actual = float(pd.to_numeric(df_view["balance actual"], errors="coerce").fillna(0.0).sum()) if "balance actual" in df_view.columns else 0.0
                        tot_profit = float(pd.to_numeric(df_view["ProfitAcum"], errors="coerce").fillna(0.0).sum()) if "ProfitAcum" in df_view.columns else 0.0
                        total_row = {
                            "exchange": "",
                            "asset": "TOTAL",
                            "anchor": self.anchor,
                            "balance inicial": f"{tot_init:.6f}",
                            "balance actual": f"{tot_actual:.6f}",
                            "ProfitAcum": f"{tot_profit:.6f}",
                            "iter profit%": "",
                            "accion": "",
                        }
                        df_view = pd.concat([df_view, pd.DataFrame([total_row])], ignore_index=True)
                except Exception:
                    pass
                text = header + "\n" + self._format_table(df_view, disp_cols)
            tmp_path = self.output_log + ".tmp"
            # Write to temp first
            with open(tmp_path, "w", encoding="utf-8") as fh:
                fh.write(text + "\n")
                fh.flush()
                try:
                    os.fsync(fh.fileno())
                except Exception:
                    pass
            # Try atomic replace; on Windows this can fail if a reader holds the file open
            try:
                os.replace(tmp_path, self.output_log)
            except Exception:
                try:
                    with open(self.output_log, "w", encoding="utf-8") as fh2:
                        fh2.write(text + "\n")
                        fh2.flush()
                        try:
                            os.fsync(fh2.fileno())
                        except Exception:
                            pass
                finally:
                    try:
                        if os.path.exists(tmp_path):
                            os.remove(tmp_path)
                    except Exception:
                        pass
        except Exception as e:
            logger.warning("Failed to write log snapshot %s: %s", self.output_log, e)

    def _append_history(self, df: pd.DataFrame) -> None:
        if not self.history_log_enabled:
            return
        try:
            os.makedirs(os.path.dirname(self.history_log_path), exist_ok=True)
            os.makedirs(os.path.dirname(self.history_csv_path), exist_ok=True)
            # Prepare header and table text
            title = "SCALPIN - Saldos por exchange/asset"
            now_utc = datetime.now(timezone.utc)
            if not hasattr(self, "_t0") or self._t0 is None:
                self._t0 = now_utc
            elapsed = now_utc - self._t0
            iter_total = self.max_iterations if self.max_iterations else "Γê₧"
            header = f"{title}\nanchor={self.anchor} | exchanges={','.join(self.exchanges)} | iter {self.iteration}/{iter_total} | elapsed={str(elapsed).split('.')[0]} | ts={now_utc.isoformat()}"
            if self.fast_mode:
                disp_cols = ["exchange", "asset", "anchor", "balance inicial", "balance actual", "ProfitAcum", "iter profit%", "accion"]
                view_rows: List[Dict[str, str]] = []
                total_init = 0.0
                total_actual = 0.0
                total_profit = 0.0
                for r in df.to_dict(orient="records"):
                    key = (str(r.get("exchange", "")), str(r.get("asset", "")))
                    init_bal = self._initial_balances.get(key)
                    try:
                        bal_actual = float(r.get("valor_anchor", 0.0) or 0.0)
                    except Exception:
                        bal_actual = 0.0
                    profit_acum = (bal_actual - float(init_bal)) if init_bal is not None else 0.0
                    try:
                        total_init += float(init_bal) if init_bal is not None else 0.0
                    except Exception:
                        pass
                    total_actual += float(bal_actual or 0.0)
                    total_profit += float(profit_acum or 0.0)
                    view_rows.append({
                        "exchange": r.get("exchange", ""),
                        "asset": r.get("asset", ""),
                        "anchor": r.get("anchor", ""),
                        "balance inicial": (f"{float(init_bal):.6f}" if init_bal is not None else ""),
                        "balance actual": f"{bal_actual:.6f}",
                        "ProfitAcum": f"{profit_acum:.6f}",
                        "iter profit%": f"{float(r.get('profit_pct', 0.0)):.4f}%",
                        "accion": r.get("accion", ""),
                    })
                if view_rows:
                    view_rows.append({
                        "exchange": "",
                        "asset": "TOTAL",
                        "anchor": self.anchor,
                        "balance inicial": f"{total_init:.6f}",
                        "balance actual": f"{total_actual:.6f}",
                        "ProfitAcum": f"{total_profit:.6f}",
                        "iter profit%": "",
                        "accion": "",
                    })
                text = header + "\n" + self._format_table(pd.DataFrame(view_rows), disp_cols) + "\n\n"
            else:
                df_view = df.copy()
                def _init_bal_r(row):
                    return self._initial_balances.get((str(row.get("exchange")), str(row.get("asset"))))
                try:
                    df_view["balance inicial"] = df_view.apply(_init_bal_r, axis=1)
                except Exception:
                    df_view["balance inicial"] = None
                try:
                    df_view["balance actual"] = df_view["valor_anchor"].astype(float)
                except Exception:
                    df_view["balance actual"] = df_view["valor_anchor"]
                try:
                    df_view["ProfitAcum"] = (df_view["balance actual"].astype(float) - df_view["balance inicial"].astype(float))
                except Exception:
                    try:
                        df_view["ProfitAcum"] = df_view["balance actual"].astype(float) - df_view["balance inicial"].fillna(0.0).astype(float)
                    except Exception:
                        df_view["ProfitAcum"] = 0.0
                try:
                    df_view["iter profit%"] = df_view["profit_pct"].apply(lambda x: f"{float(x):.4f}%")
                except Exception:
                    df_view["iter profit%"] = df_view.get("profit_pct", [])
                # Append totals row
                try:
                    if not df_view.empty:
                        tot_init = float(pd.to_numeric(df_view["balance inicial"], errors="coerce").fillna(0.0).sum()) if "balance inicial" in df_view.columns else 0.0
                        tot_actual = float(pd.to_numeric(df_view["balance actual"], errors="coerce").fillna(0.0).sum()) if "balance actual" in df_view.columns else 0.0
                        tot_profit = float(pd.to_numeric(df_view["ProfitAcum"], errors="coerce").fillna(0.0).sum()) if "ProfitAcum" in df_view.columns else 0.0
                        total_row = {
                            "exchange": "",
                            "asset": "TOTAL",
                            "anchor": self.anchor,
                            "balance inicial": f"{tot_init:.6f}",
                            "balance actual": f"{tot_actual:.6f}",
                            "ProfitAcum": f"{tot_profit:.6f}",
                            "iter profit%": "",
                            "accion": "",
                        }
                        df_view = pd.concat([df_view, pd.DataFrame([total_row])], ignore_index=True)
                except Exception:
                    pass
                disp_cols = ["exchange", "asset", "anchor", "balance inicial", "balance actual", "ProfitAcum", "iter profit%", "accion"]
                text = header + "\n" + self._format_table(df_view, disp_cols) + "\n\n"
            # Append to text history log
            with open(self.history_log_path, "a", encoding="utf-8") as fh:
                fh.write(text)
                try:
                    fh.flush()
                    os.fsync(fh.fileno())
                except Exception:
                    pass
            # Append to CSV history with timestamp
            if self.fast_mode:
                cols_csv = ["exchange", "asset", "anchor", "valor_anchor", "profit_pct", "accion", "ts"]
                header_needed = not os.path.exists(self.history_csv_path) or os.path.getsize(self.history_csv_path) == 0
                with open(self.history_csv_path, "a", newline="", encoding="utf-8") as fh:
                    writer = csv.DictWriter(fh, fieldnames=cols_csv)
                    if header_needed:
                        writer.writeheader()
                    for r in df.to_dict(orient="records"):
                        row = {k: r.get(k, "") for k in cols_csv}
                        row["ts"] = now_utc.isoformat()
                        writer.writerow(row)
                    try:
                        fh.flush()
                        os.fsync(fh.fileno())
                    except Exception:
                        pass
            else:
                df_csv = df.copy()
                df_csv["ts"] = now_utc.isoformat()
                header_needed = not os.path.exists(self.history_csv_path) or os.path.getsize(self.history_csv_path) == 0
                # Write to temp then append atomically by replacing a concatenated file is heavy; instead ensure flush
                with open(self.history_csv_path, "a", encoding="utf-8", newline="") as fh:
                    if header_needed:
                        fh.write(",".join(df_csv.columns.tolist()) + "\n")
                    for _, row in df_csv.iterrows():
                        fh.write(",".join(str(row[c]) for c in df_csv.columns.tolist()) + "\n")
                    try:
                        fh.flush()
                        os.fsync(fh.fileno())
                    except Exception:
                        pass
        except Exception as e:
            logger.warning("Failed to append to history logs: %s", e)

    def _format_table(self, df: pd.DataFrame, cols: List[str]) -> str:
        try:
            df2 = df[cols]
        except Exception:
            df2 = df
        if tabulate is not None:
            try:
                # When DataFrame is empty, some formats (like 'plain') can yield blank output; fallback to ASCII grid
                if getattr(df2, "empty", False):
                    raise ValueError("empty-df-fallback")
                return tabulate(df2.values.tolist(), headers=cols, tablefmt=self.table_format, floatfmt=".6f")
            except Exception:
                pass
        # Fallback to ASCII grid so borders are always shown
        return self._ascii_grid(df2, cols)

    def _ascii_grid(self, df: pd.DataFrame, cols: List[str]) -> str:
        # Ensure we work on a copy with only requested columns
        try:
            data = df[cols].copy()
        except Exception:
            data = df.copy()
        # Compute column widths
        col_widths = {}
        for c in data.columns:
            max_cell = max([len(str(x)) for x in data[c].astype(str).tolist()] + [len(str(c))]) if len(data) else len(str(c))
            col_widths[c] = max_cell
        # Build border and rows
        def border_line():
            segments = ["+" + ("-" * (col_widths[c] + 2)) for c in data.columns]
            return "".join(segments) + "+"
        def row_line(values):
            segments = []
            for c, v in zip(data.columns, values):
                s = str(v)
                segments.append("| " + s.ljust(col_widths[c]) + " ")
            return "".join(segments) + "|"
        lines = [border_line(), row_line(list(data.columns)), border_line()]
        if len(data):
            for _, row in data.iterrows():
                lines.append(row_line([row[c] for c in data.columns]))
        lines.append(border_line())
        return "\n".join(lines)

    def run(self) -> None:
        logger.info(
            "ScalpinMonitor start | exchanges=%s | anchor=%s | poll=%ss | min_value_anchor=%.4f",
            ",".join(self.exchanges), self.anchor, self.poll_sec, self.min_value_anchor,
        )
        self._t0 = datetime.now(timezone.utc)
        while True:
            try:
                t0 = time.perf_counter()
                rows = self._build_table_rows()
                t1 = time.perf_counter()
                # Decide actions for next iteration number
                next_iter = self.iteration + 1
                # Always seed first iteration outputs so .log files are not empty
                seed_first_output = (self.iteration == 0)
                do_print = seed_first_output or (self.render_every_n <= 1) or (next_iter % self.render_every_n == 0)
                do_snapshot = seed_first_output or (self.snapshot_every_n <= 1) or (next_iter % self.snapshot_every_n == 0)
                do_log = seed_first_output or ((self.log_every_n > 0) and (next_iter % self.log_every_n == 0))
                do_hist = seed_first_output or ((self.history_every_n > 0) and (next_iter % self.history_every_n == 0))
                df = None
                t2 = t1
                if do_print or do_log or do_hist:
                    df = self._render(rows, print_console=do_print)
                    t2 = time.perf_counter()
                ms_snapshot = 0.0
                ms_log = 0.0
                ms_hist = 0.0
                if do_snapshot:
                    self._write_snapshot(rows)
                    t3 = time.perf_counter()
                    ms_snapshot = (t3 - t2) * 1000.0
                    t2 = t3
                if do_log and df is not None:
                    self._write_log_snapshot(df)
                    t4 = time.perf_counter()
                    ms_log = (t4 - t2) * 1000.0
                    t2 = t4
                if do_hist and df is not None:
                    self._append_history(df)
                    t5 = time.perf_counter()
                    ms_hist = (t5 - t2) * 1000.0
                    t2 = t5
                t_end = time.perf_counter()
                # Perf metrics for this iteration
                perf = {
                    "iter": self.iteration,
                    "ts": datetime.now(timezone.utc).isoformat(),
                    "row_count": len(rows),
                    "ms_rows": (t1 - t0) * 1000.0,
                    "ms_render": (0.0 if (not do_print and not do_log and not do_hist) else (t2 - t1 - ms_snapshot - ms_log - ms_hist)),
                    "ms_snapshot": ms_snapshot,
                    "ms_log": ms_log,
                    "ms_hist": ms_hist,
                    "ms_total": (t_end - t0) * 1000.0,
                }
                self._last_perf = perf
                self._perf_hist.append(perf)
                if len(self._perf_hist) > self.perf_window:
                    self._perf_hist.pop(0)
                self._maybe_write_perf_csv(perf)
            except KeyboardInterrupt:
                logger.info("Interrupted by user. Bye.")
                return
            except Exception as e:
                logger.warning("Loop error: %s", e)
            # Termination controls
            if self.max_iterations and self.iteration >= self.max_iterations:
                logger.info("Reached max_iterations=%d. Stopping.", self.max_iterations)
                return
            if self.run_duration_sec and (datetime.now(timezone.utc) - self._t0) >= timedelta(seconds=self.run_duration_sec):
                logger.info("Reached run_duration_sec=%.1f. Stopping.", self.run_duration_sec)
                return
            time.sleep(max(0.0, float(self.poll_sec)))

    def _maybe_write_perf_csv(self, perf: dict) -> None:
        if not self.perf_csv_enabled:
            return
        try:
            out_dir = os.path.dirname(self.perf_csv_path)
            if out_dir and not os.path.isdir(out_dir):
                os.makedirs(out_dir, exist_ok=True)
            header_needed = not os.path.exists(self.perf_csv_path) or os.path.getsize(self.perf_csv_path) == 0
            cols = [
                "iter", "ts", "row_count",
                "ms_rows", "ms_render", "ms_snapshot", "ms_log", "ms_hist", "ms_total",
            ]
            with open(self.perf_csv_path, "a", newline="", encoding="utf-8") as fh:
                wr = csv.DictWriter(fh, fieldnames=cols)
                if header_needed:
                    wr.writeheader()
                wr.writerow({k: perf.get(k, "") for k in cols})
                try:
                    fh.flush()
                    os.fsync(fh.fileno())
                except Exception:
                    pass
        except Exception as e:
            logger.debug("perf csv write failed: %s", e)


def main() -> None:
    # Resolve config path relative to CWD
    cfg_path = os.environ.get("SCALPIN_CONFIG") or os.path.join(os.getcwd(), "scalpin.yaml")
    mon = ScalpinMonitor(config_path=cfg_path)
    # Optional environment overrides to support short test runs without editing YAML
    try:
        _steps = os.environ.get("SCALPIN_RUN_STEPS")
        if _steps:
            mon.max_iterations = int(_steps)
        _dur = os.environ.get("SCALPIN_RUN_DURATION_SEC")
        if _dur:
            mon.run_duration_sec = float(_dur)
    except Exception:
        pass
    mon.run()


if __name__ == "__main__":
    main()
