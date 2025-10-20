from __future__ import annotations

import os
import sys
import time
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta, timezone
import csv
from concurrent.futures import ThreadPoolExecutor, as_completed

import ccxt  # type: ignore
import yaml
import pandas as pd
from dotenv import load_dotenv
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
            bucket = bal.get("total") or bal.get("free") or {}
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
        # Load .env at startup
        try:
            load_dotenv(override=False)
            # Also attempt parent .env if running inside a subfolder
            cwd = os.getcwd()
            parent_env = os.path.join(os.path.dirname(cwd), ".env")
            if os.path.exists(parent_env):
                load_dotenv(dotenv_path=parent_env, override=False)
        except Exception:
            pass
        self.cfg = parse_yaml(config_path)
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
        default_out = os.path.join(os.getcwd(), "artifacts", "scalpin", "current_scalpin.csv")
        self.output_csv: str = str(self.cfg.get("output_csv") or default_out)
        # Output text log snapshot (overwritten every tick)
        default_log = os.path.join(os.getcwd(), "artifacts", "scalpin", "current_scalpin.log")
        self.output_log: str = str(self.cfg.get("output_log") or default_log)
        # Persistent history logs (append-only)
        default_hist_log = os.path.join(os.getcwd(), "artifacts", "scalpin", "scalpin_history.log")
        default_hist_csv = os.path.join(os.getcwd(), "artifacts", "scalpin", "scalpin_history.csv")
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
        default_perf_csv = os.path.join(os.getcwd(), "artifacts", "scalpin", "scalpin_perf.csv")
        self.perf_csv_path = str(self.cfg.get("perf_csv_path") or default_perf_csv)
        self.perf_csv_enabled = bool(self.cfg.get("perf_csv_enabled", True))

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

        def worker(ex_id: str, client: ExchangeClient) -> List[dict]:
            local_rows: List[dict] = []
            balances = client.fetch_balances()
            if not balances:
                return local_rows
            balances = self._filter_assets(balances)
            assets = list(balances.keys())
            prices = client.fetch_prices_in_anchor(assets)
            for asset, bal in balances.items():
                if asset.upper() == self.anchor:
                    continue
                price = prices.get(asset.upper())
                if price is None or price <= 0:
                    continue
                value_anchor = float(bal) * float(price)
                if self.min_value_anchor and value_anchor < self.min_value_anchor:
                    continue
                key = (ex_id, asset.upper())
                prev_px = self._last_price.get(key)
                if prev_px and prev_px > 0:
                    try:
                        profit_pct = (float(price) / float(prev_px) - 1.0) * 100.0
                    except Exception:
                        profit_pct = 0.0
                else:
                    profit_pct = 0.0
                self._last_price[key] = float(price)
                accion = ""
                if profit_pct is not None and profit_pct > float(self.profit_action_threshold_pct):
                    accion = f"@{ex_id} swap {asset.upper()}->{self.anchor}->{asset.upper()}"
                    if accion:
                        log_path = os.path.join(os.getcwd(), "artifacts", "arbitraje", "logs", "swapper.log")
                        fh = None
                        try:
                            fh = open(log_path, "ab")
                        except Exception:
                            fh = None
                        try:
                            __import__("subprocess").Popen(
                                [
                                    sys.executable,
                                    "-m",
                                    "arbitraje.swapper",
                                    "--config",
                                    os.path.join(os.getcwd(), "projects", "arbitraje", "swapper.live.yaml"),
                                    "--exchange",
                                    ex_id,
                                    "--path",
                                    f"{asset.upper()}->{self.anchor}->{asset.upper()}",
                                ],
                                env=dict(os.environ, PYTHONPATH=os.path.join(os.getcwd(), "projects", "arbitraje", "src")),
                                stdout=fh if fh is not None else None,
                                stderr=__import__("subprocess").STDOUT if fh is not None else None,
                            )
                        finally:
                            try:
                                if fh is not None:
                                    fh.flush()
                                    os.fsync(fh.fileno())
                                    fh.close()
                            except Exception:
                                pass
                local_rows.append(
                    {
                        "exchange": ex_id,
                        "asset": asset.upper(),
                        "anchor": self.anchor,
                        "valor_anchor": round(value_anchor, 8),
                        "profit_pct": round(profit_pct, 6),
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
        return rows

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
        iter_total = self.max_iterations if self.max_iterations else "∞"
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
            return pd.DataFrame(columns=["exchange", "asset", "anchor", "valor_anchor", "profit_pct", "accion", "ts"])
        try:
            df = pd.DataFrame(rows, columns=["exchange", "asset", "anchor", "valor_anchor", "profit_pct", "accion"])
        except Exception:
            df = pd.DataFrame(rows)
        # Pretty print
        if self.fast_mode:
            # Build rows directly to avoid DataFrame overhead
            cols = ["exchange", "asset", "anchor", "valor_anchor", "profit", "accion"]
            view_rows: List[Dict[str, str]] = []
            for r in rows:
                view_rows.append({
                    "exchange": r.get("exchange", ""),
                    "asset": r.get("asset", ""),
                    "anchor": r.get("anchor", ""),
                    "valor_anchor": f"{float(r.get('valor_anchor', 0.0)):.6f}",
                    "profit": f"{float(r.get('profit_pct', 0.0)):.4f}%",
                    "accion": r.get("accion", ""),
                })
            if print_console:
                print(self._format_table(pd.DataFrame(view_rows), cols))
        else:
            df_view = df.copy()
            try:
                df_view["profit"] = df_view["profit_pct"].apply(lambda x: f"{float(x):.4f}%")
            except Exception:
                df_view["profit"] = df_view.get("profit_pct", [])
            cols = ["exchange", "asset", "anchor", "valor_anchor", "profit", "accion"]
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
                cols = ["exchange", "asset", "anchor", "valor_anchor", "profit_pct", "accion"]
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
                df = pd.DataFrame(rows, columns=["exchange", "asset", "anchor", "valor_anchor", "profit_pct", "accion"]) if rows else pd.DataFrame(columns=["exchange", "asset", "anchor", "valor_anchor", "profit_pct", "accion"])            
                df.to_csv(tmp_path, index=False)
            os.replace(tmp_path, self.output_csv)
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
            iter_total = self.max_iterations if self.max_iterations else "∞"
            header = f"{title}\nanchor={self.anchor} | exchanges={','.join(self.exchanges)} | iter {self.iteration}/{iter_total} | elapsed={str(elapsed).split('.')[0]} | ts={now_utc.isoformat()}"
            if self.fast_mode:
                cols = ["exchange", "asset", "anchor", "valor_anchor", "profit", "accion"]
                view_rows: List[Dict[str, str]] = []
                for r in df.to_dict(orient="records"):
                    view_rows.append({
                        "exchange": r.get("exchange", ""),
                        "asset": r.get("asset", ""),
                        "anchor": r.get("anchor", ""),
                        "valor_anchor": f"{float(r.get('valor_anchor', 0.0)):.6f}",
                        "profit": f"{float(r.get('profit_pct', 0.0)):.4f}%",
                        "accion": r.get("accion", ""),
                    })
                text = header + "\n" + self._format_table(pd.DataFrame(view_rows), cols)
            else:
                df_view = df.copy()
                try:
                    df_view["profit"] = df_view["profit_pct"].apply(lambda x: f"{float(x):.4f}%")
                except Exception:
                    df_view["profit"] = df_view.get("profit_pct", [])
                cols = ["exchange", "asset", "anchor", "valor_anchor", "profit", "accion"]
                cols = [c for c in cols if c in df_view.columns]
                text = header + "\n" + self._format_table(df_view, cols)
            tmp_path = self.output_log + ".tmp"
            with open(tmp_path, "w", encoding="utf-8") as fh:
                fh.write(text + "\n")
                fh.flush()
                try:
                    os.fsync(fh.fileno())
                except Exception:
                    pass
            os.replace(tmp_path, self.output_log)
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
            iter_total = self.max_iterations if self.max_iterations else "∞"
            header = f"{title}\nanchor={self.anchor} | exchanges={','.join(self.exchanges)} | iter {self.iteration}/{iter_total} | elapsed={str(elapsed).split('.')[0]} | ts={now_utc.isoformat()}"
            if self.fast_mode:
                cols = ["exchange", "asset", "anchor", "valor_anchor", "profit", "accion"]
                view_rows: List[Dict[str, str]] = []
                for r in df.to_dict(orient="records"):
                    view_rows.append({
                        "exchange": r.get("exchange", ""),
                        "asset": r.get("asset", ""),
                        "anchor": r.get("anchor", ""),
                        "valor_anchor": f"{float(r.get('valor_anchor', 0.0)):.6f}",
                        "profit": f"{float(r.get('profit_pct', 0.0)):.4f}%",
                        "accion": r.get("accion", ""),
                    })
                text = header + "\n" + self._format_table(pd.DataFrame(view_rows), cols) + "\n\n"
            else:
                df_view = df.copy()
                try:
                    df_view["profit"] = df_view["profit_pct"].apply(lambda x: f"{float(x):.4f}%")
                except Exception:
                    df_view["profit"] = df_view.get("profit_pct", [])
                cols = ["exchange", "asset", "anchor", "valor_anchor", "profit", "accion"]
                cols = [c for c in cols if c in df_view.columns]
                text = header + "\n" + self._format_table(df_view, cols) + "\n\n"
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
                do_print = (self.render_every_n <= 1) or (next_iter % self.render_every_n == 0)
                do_snapshot = (self.snapshot_every_n <= 1) or (next_iter % self.snapshot_every_n == 0)
                do_log = (self.log_every_n > 0) and (next_iter % self.log_every_n == 0)
                do_hist = (self.history_every_n > 0) and (next_iter % self.history_every_n == 0)
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
    mon.run()


if __name__ == "__main__":
    main()
