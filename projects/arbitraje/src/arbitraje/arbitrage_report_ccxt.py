from __future__ import annotations

import argparse, time, math, os
import concurrent.futures
from typing import List, Dict, Tuple
import sys
import logging

import ccxt
import pandas as pd
from tabulate import tabulate

from . import paths
from . import binance_api
try:
    # Load .env from repo root and project root if present
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=str(paths.MONOREPO_ROOT / ".env"), override=False)
    load_dotenv(dotenv_path=str(paths.PROJECT_ROOT / ".env"), override=False)
except Exception:
    pass


# ----------------------
# Logging configuration
# ----------------------
logger = logging.getLogger("arbitraje_ccxt")
if not logger.handlers:
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    logger.addHandler(sh)
    try:
        paths.LOGS_DIR.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(paths.LOGS_DIR / "arbitraje_ccxt.log", encoding="utf-8")
        fh.setFormatter(fmt)
        logger.addHandler(fh)
    except Exception:
        pass


# ----------------------
# Helpers
# ----------------------
STABLE_BASES = {"USDT", "USDC", "BUSD", "TUSD", "FDUSD", "DAI", "USTC"}


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
        val = ex.has.get(feature)
        return bool(val)
    except Exception:
        return False


def load_exchange(ex_id: str, timeout_ms: int) -> ccxt.Exchange:
    cls = getattr(ccxt, ex_id)
    ex = cls({"enableRateLimit": True})
    try:
        ex.timeout = int(timeout_ms)
    except Exception:
        pass
    return ex


def creds_from_env(ex_id: str) -> dict:
    """Return ccxt credential dict if env vars for the exchange exist; else {}."""
    env = os.environ
    ex_id = (ex_id or "").lower()
    try:
        if ex_id == "binance":
            k = env_get_stripped("BINANCE_API_KEY"); s = env_get_stripped("BINANCE_API_SECRET")
            if k and s:
                return {"apiKey": k, "secret": s}
        elif ex_id == "bybit":
            k = env_get_stripped("BYBIT_API_KEY"); s = env_get_stripped("BYBIT_API_SECRET")
            if k and s:
                return {"apiKey": k, "secret": s}
        elif ex_id == "bitget":
            k = env_get_stripped("BITGET_API_KEY"); s = env_get_stripped("BITGET_API_SECRET"); p = env_get_stripped("BITGET_PASSWORD")
            if k and s and p:
                return {"apiKey": k, "secret": s, "password": p}
        elif ex_id == "coinbase":
            # Coinbase Advanced
            k = env_get_stripped("COINBASE_API_KEY"); s = env_get_stripped("COINBASE_API_SECRET"); p = env_get_stripped("COINBASE_API_PASSWORD")
            if k and s and p:
                return {"apiKey": k, "secret": s, "password": p}
    except Exception:
        pass
    return {}


def load_exchange_auth_if_available(ex_id: str, timeout_ms: int, use_auth: bool = False) -> ccxt.Exchange:
    """Load an exchange; if use_auth, pass credentials from env when available."""
    cls = getattr(ccxt, ex_id)
    cfg = {"enableRateLimit": True}
    if use_auth:
        cfg.update(creds_from_env(ex_id))
    ex = cls(cfg)
    try:
        ex.timeout = int(timeout_ms)
    except Exception:
        pass
    return ex


def fetch_quote_balance(ex: ccxt.Exchange, quote: str, kind: str = "free") -> float | None:
    """Fetch QUOTE balance from an authenticated ccxt exchange instance. Returns None on error/missing."""
    try:
        bal = ex.fetch_balance()
        bucket = bal.get("free") if (kind or "free").lower() == "free" else bal.get("total")
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


def get_rate_and_qvol(a: str, b: str, tickers: Dict[str, dict], fee_pct: float, require_topofbook: bool = False) -> Tuple[float | None, float | None]:
    """Return (rate, quote_volume) for converting a->b using top-of-book where possible.

    - If require_topofbook=True, do not fallback to 'last' when bid/ask missing.
    - quote_volume is taken from the market used (direct a/b or inverse b/a).
    """
    a = a.upper(); b = b.upper()
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
) -> Tuple[List[Tuple[int, int, float]], Dict[Tuple[int, int], float]]:
    cur_index = {c: i for i, c in enumerate(currencies)}
    edges: List[Tuple[int, int, float]] = []
    rate_map: Dict[Tuple[int, int], float] = {}
    for u in currencies:
        for v in currencies:
            if u == v:
                continue
            r, qv = get_rate_and_qvol(u, v, tickers, fee_pct, require_topofbook)
            if r and r > 0:
                if min_quote_vol > 0.0:
                    if qv is None or qv < min_quote_vol:
                        continue
                u_i = cur_index[u]; v_i = cur_index[v]
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


def resolve_exchanges(arg: str, ex_limit: int | None = None) -> List[str]:
    arg = (arg or "").strip().lower()
    if not arg or arg == "trusted":
        return ["binance", "bitget", "bybit","coinbase"]
    if arg in ("trusted-plus", "trusted_plus", "trustedplus"):
        return ["binance", "bitget", "bybit","coinbase"]
    if arg == "all":
        xs = list(ccxt.exchanges)
        if ex_limit and ex_limit > 0:
            xs = xs[: ex_limit]
        return xs
    # explicit comma-separated list
    return [s.strip().lower() for s in arg.split(",") if s.strip()]


# ----------------------
# Main
# ----------------------
def main() -> None:
    parser = argparse.ArgumentParser(description="Arbitraje (ccxt) - modes: tri | bf | balance | health")
    parser.add_argument("--mode", choices=["tri", "bf", "balance", "health"], default="bf")
    parser.add_argument("--ex", type=str, default="trusted", help="trusted | trusted-plus | all | comma list")
    parser.add_argument("--exclude_ex", type=str, default="", help="Comma-separated exchanges to exclude after resolution (e.g., 'bitso,bitstamp')")
    parser.add_argument("--quote", type=str, default="USDT")
    parser.add_argument("--max", type=int, default=200, dest="max")
    parser.add_argument("--timeout", type=int, default=20000, help="ccxt timeout (ms)")
    parser.add_argument("--sleep", type=float, default=0.12, help="sleep between requests (s)")
    parser.add_argument("--inv", type=float, default=1000.0)
    parser.add_argument("--top", type=int, default=25)

    # Inter-exchange filters and fees
    parser.add_argument("--min_spread", type=float, default=0.5)
    parser.add_argument("--min_price", type=float, default=0.0)
    parser.add_argument("--include_stables", action="store_true")
    parser.add_argument("--min_sources", type=int, default=2)
    parser.add_argument("--min_quote_vol", type=float, default=0.0)
    parser.add_argument("--vol_strict", action="store_true")
    parser.add_argument("--max_spread_cap", type=float, default=10.0)
    parser.add_argument("--buy_fee", type=float, default=0.10, help="%")
    parser.add_argument("--sell_fee", type=float, default=0.10, help="%")
    parser.add_argument("--xfer_fee_pct", type=float, default=0.0, help="% additional xfer cost")
    parser.add_argument("--per_ex_timeout", type=float, default=6.0, help="seconds per-exchange budget when iterating symbols")
    parser.add_argument("--per_ex_limit", type=int, default=0, help="max symbols per exchange iteration (0 = no cap)")
    parser.add_argument("--ex_limit", type=int, default=0, help="cap number of exchanges when ex=all")

    # Triangular
    parser.add_argument("--tri_fee", type=float, default=0.10, help="per-hop fee %")
    parser.add_argument("--tri_currencies_limit", type=int, default=35)
    parser.add_argument("--tri_min_net", type=float, default=0.5)
    parser.add_argument("--tri_top", type=int, default=5)
    parser.add_argument("--tri_require_topofbook", action="store_true", help="Use only bid/ask; no 'last' fallback")
    parser.add_argument("--tri_min_quote_vol", type=float, default=0.0, help="Filter hops by min quote volume")

    # Bellman-Ford
    parser.add_argument("--bf_fee", type=float, default=0.10, help="per-hop fee %")
    parser.add_argument("--bf_currencies_limit", type=int, default=35)
    parser.add_argument("--bf_rank_by_qvol", action="store_true", help="Rank and select currencies by aggregate quote volume to build a higher-quality universe")
    parser.add_argument("--bf_min_net", type=float, default=0.5)
    parser.add_argument("--bf_min_net_per_hop", type=float, default=0.0, help="Descarta ciclos BF cuyo net/hop sea inferior a este umbral (%)")
    parser.add_argument("--bf_top", type=int, default=5)
    parser.add_argument("--bf_persist_top_csv", action="store_true", help="Persistir las top oportunidades por iteración en un CSV acumulado")
    parser.add_argument("--bf_require_quote", action="store_true")
    parser.add_argument("--bf_min_hops", type=int, default=0)
    parser.add_argument("--bf_max_hops", type=int, default=0)
    parser.add_argument("--bf_require_topofbook", action="store_true", help="Use only bid/ask; no 'last' fallback")
    parser.add_argument("--bf_min_quote_vol", type=float, default=0.0, help="Filter edges by min quote volume")
    parser.add_argument("--bf_threads", type=int, default=1, help="Threads for per-exchange BF scanning (1 = no threading, 0 or negative = one thread per exchange)")
    parser.add_argument("--bf_debug", action="store_true", help="Print BF debug details: currencies, edges, and cycles counts per exchange")
    parser.add_argument("--bf_require_dual_quote", action="store_true", help="When multiple anchors (e.g. USDT,USDC) are allowed, include only bases that have markets against ALL anchors")
    parser.add_argument("--use_balance", action="store_true", help="Use authenticated QUOTE balance (if available) for est_after; min(inv, balance)")
    parser.add_argument("--balance_kind", choices=["free", "total"], default="free", help="Balance kind when --use_balance")

    # BF simulation (compounding) across iterations
    parser.add_argument("--simulate_compound", action="store_true", help="Simulate compounding: keep a running QUOTE balance and apply one selected BF opportunity per iteration (no real trades)")
    parser.add_argument("--simulate_start", type=float, default=None, help="Starting QUOTE balance for simulation (defaults to --inv if omitted)")
    parser.add_argument(
        "--simulate_select",
        choices=["best", "first"],
        default="best",
        help="How to choose the opportunity each iteration: best = highest net %; first = first found",
    )
    parser.add_argument("--simulate_from_wallet", action="store_true", help="Initialize simulation from wallet balance (USDT/USDC); requires exchange credentials")
    parser.add_argument("--simulate_prefer", choices=["USDT", "USDC", "auto"], default="auto", help="Preferred anchor when using --simulate_from_wallet; auto = choose with higher balance")
    parser.add_argument("--simulate_auto_switch", action="store_true", help="Auto-switch simulation anchor (USDT/USDC) to the currency with the best available cycle each iteration")
    parser.add_argument("--simulate_switch_threshold", type=float, default=0.0, help="Minimum additional net %% required to switch anchor vs current anchor's best (default 0.0)")

    # Repeat / UX
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--repeat_sleep", type=float, default=3.0)
    parser.add_argument("--console_clear", action="store_true")
    parser.add_argument("--no_console_clear", action="store_true", help="Don't clear console even if --console_clear is set (or set ARBITRAJE_NO_CLEAR=1)")
    # Balance provider selection
    parser.add_argument("--balance_provider", choices=["ccxt", "native", "connector", "bitget_sdk"], default="ccxt", help="Provider for --mode balance: ccxt (default), native (direct REST for binance), connector (official Binance SDK Spot), or bitget_sdk (official Bitget SDK)")
    # Filter exchanges to only those with credentials
    parser.add_argument("--ex_auth_only", action="store_true", help="Only include exchanges that have API credentials present in environment")
    # Allow multiple anchor quotes (e.g., USDT and USDC)
    parser.add_argument("--bf_allowed_quotes", type=str, default=None, help="Comma-separated list of allowed anchor quotes for BF cycles, e.g. 'USDT,USDC' (defaults to QUOTE only)")

    args = parser.parse_args()

    QUOTE = args.quote.upper()
    UNIVERSE_LIMIT = max(1, int(args.max))
    EX_IDS = resolve_exchanges(args.ex, args.ex_limit)
    # Exclude exchanges explicitly if requested
    if args.exclude_ex:
        try:
            excludes = {e.strip().lower() for e in args.exclude_ex.split(',') if e.strip()}
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
            logger.warning("--ex_auth_only: ninguna exchange con credenciales; nada que hacer")
            return
        EX_IDS = ex_ids_auth

    # Determine allowed anchor quotes for BF cycles
    allowed_quotes: List[str] = []
    if args.bf_allowed_quotes:
        try:
            allowed_quotes = [q.strip().upper() for q in args.bf_allowed_quotes.split(",") if q.strip()]
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
    do_console_clear = bool(args.console_clear) and not bool(args.no_console_clear) and not bool(env_no_clear)

    logger.info("Mode=%s | quote=%s | ex=%s", args.mode, QUOTE, ",".join(EX_IDS))

    # Pre-create and cache ccxt exchange instances (and markets) to speed up repeated iterations
    ex_instances: Dict[str, ccxt.Exchange] = {}
    try:
        preload_for_modes = {"bf", "tri"}
        if args.mode in preload_for_modes:
            for _ex in EX_IDS:
                try:
                    inst = load_exchange_auth_if_available(_ex, args.timeout, use_auth=bool(getattr(args, "use_balance", False)))
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
                    ex_auth = load_exchange_auth_if_available(ex_id, args.timeout, use_auth=True)
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
                    pairs = binance_api.get_convert_pairs(api_key, api_secret, timeout=args.timeout)
                    extra_cols["convert_pairs_count"] = len(pairs) if isinstance(pairs, list) else None
                    # Persist to CSV
                    try:
                        if isinstance(pairs, list) and pairs:
                            df_pairs = pd.DataFrame(pairs)
                            df_pairs.to_csv(paths.OUTPUTS_DIR / "binance_convert_pairs.csv", index=False)
                    except Exception:
                        pass
                except Exception:
                    extra_cols["convert_pairs_count"] = None
                try:
                    # Convert asset info (USER_DATA signed)
                    asset_info = binance_api.get_convert_asset_info(api_key, api_secret, timeout=args.timeout)
                    extra_cols["asset_info_count"] = len(asset_info) if isinstance(asset_info, list) else None
                    # Persist to CSV
                    try:
                        if isinstance(asset_info, list) and asset_info:
                            df_assets = pd.DataFrame(asset_info)
                            df_assets.to_csv(paths.OUTPUTS_DIR / "binance_convert_asset_info.csv", index=False)
                    except Exception:
                        pass
                except Exception:
                    extra_cols["asset_info_count"] = None
            rows.append({
                "exchange": ex_id,
                "public_ok": pub_ok,
                "markets_ok": markets_ok,
                "ticker_ok": ticker_ok,
                "status_ok": status_ok,
                "time_ok": time_ok,
                "creds_present": creds_present,
                "balance_ok": balance_ok,
                "nonzero_assets_count": nonzero_assets_count,
                "nonzero_assets_sample": ",".join(nonzero_assets_sample) if nonzero_assets_sample else None,
                **extra_cols,
            })

        # Log to console in a compact way
        headers = [
            "exchange", "public_ok", "markets_ok", "ticker_ok", "status_ok", "time_ok",
            "creds_present", "balance_ok", "nonzero_assets_count", "nonzero_assets_sample",
            "convert_pairs_count", "asset_info_count"
        ]
        df = pd.DataFrame(rows, columns=headers)
        logger.info("\n%s", tabulate(df, headers="keys", tablefmt="github", showindex=False))
        try:
            with open(health_file, "w", encoding="utf-8") as fh:
                fh.write(tabulate(df, headers="keys", tablefmt="github", showindex=False))
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
                    k = env_get_stripped("BINANCE_API_KEY"); s = env_get_stripped("BINANCE_API_SECRET")
                    if not (k and s):
                        logger.info("%s: sin credenciales en env (BINANCE_API_KEY/SECRET)", ex_id)
                        continue
                    # If native requested, use direct REST
                    if args.balance_provider == "native":
                        try:
                            acct = binance_api.get_account_balances(k, s, timeout=args.timeout)
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
                                        usdt_free = free; usdt_total = total
                                    elif asset == "USDC":
                                        usdc_free = free; usdc_total = total
                                except Exception:
                                    continue
                            nonzero.sort(key=lambda x: x[2], reverse=True)
                            top = nonzero[:20]
                            logger.info("%s balance (native, top 20 non-zero): %s", ex_id, ", ".join([f"{ccy}:{total}" for ccy, _free, total in top]) or "(vacío)")
                            logger.info("%s saldos (native): USDT free=%.8f total=%.8f | USDC free=%.8f total=%.8f", ex_id, usdt_free, usdt_total, usdc_free, usdc_total)
                            results.append({"exchange": ex_id, "assets": top})
                            continue
                        except Exception as e:
                            logger.warning("%s: native balance falló: %s; fallback a ccxt", ex_id, e)
                    # If connector requested, use official Binance Spot SDK
                    if args.balance_provider == "connector":
                        try:
                            from binance_common.configuration import ConfigurationRestAPI as BConfigRest
                            from binance_common.constants import SPOT_REST_API_PROD_URL as BSPOT_URL
                            from binance_sdk_spot.spot import Spot as BSpot
                            api_key = k
                            api_secret = s
                            # Allow overriding base path (e.g., binance.us) via env
                            base_path = env_get_stripped("BINANCE_SPOT_BASE_PATH") or env_get_stripped("BINANCE_API_BASE") or BSPOT_URL
                            cfg = BConfigRest(api_key=api_key, api_secret=api_secret, base_path=base_path)
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
                                resp = client.rest_api.get_account(omit_zero_balances=True, recv_window=recv_window)
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
                            for bal in (data.balances or []):
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
                            logger.info("%s balance (connector, top 20 non-zero): %s", ex_id, ", ".join([f"{ccy}:{total}" for ccy, _free, total in top]) or "(vacío)")
                            logger.info("%s saldos (connector): USDT free=%.8f total=%.8f | USDC free=%.8f total=%.8f", ex_id, usdt_free, usdt_total, usdc_free, usdc_total)
                            results.append({"exchange": ex_id, "assets": top, "USDT_free": usdt_free, "USDT_total": usdt_total})
                            continue
                        except Exception as e:
                            logger.warning("%s: connector balance falló: %s; fallback a ccxt", ex_id, e)
                    # Default ccxt path
                    creds = {"apiKey": k, "secret": s}
                elif ex_id == "bybit":
                    if not (env.get("BYBIT_API_KEY") and env.get("BYBIT_API_SECRET")):
                        logger.info("%s: sin credenciales en env (BYBIT_API_KEY/SECRET)", ex_id)
                        continue
                    creds = {"apiKey": env.get("BYBIT_API_KEY"), "secret": env.get("BYBIT_API_SECRET")}
                elif ex_id == "bitget":
                    if not (env.get("BITGET_API_KEY") and env.get("BITGET_API_SECRET") and env.get("BITGET_PASSWORD")):
                        logger.info("%s: sin credenciales en env (BITGET_API_KEY/SECRET/PASSWORD)", ex_id)
                        continue
                    # Official Bitget SDK provider (optional)
                    if args.balance_provider == "bitget_sdk":
                        # If SDK isn't installed, silently fallback to ccxt (avoid noisy warnings)
                        try:
                            import importlib.util as _iutil  # type: ignore
                            if _iutil.find_spec("bitget") is None:
                                logger.info("%s: bitget_sdk no instalado; usando ccxt", ex_id)
                            else:
                                # Preferred env vars
                                bg_key = env_get_stripped("BITGET_API_KEY")
                                bg_secret = env_get_stripped("BITGET_API_SECRET")
                                bg_pass = env_get_stripped("BITGET_PASSWORD")
                                # Try SDK import pattern 1
                                from bitget.openapi import Spot as BGSpot  # type: ignore
                                client = BGSpot(api_key=bg_key, secret_key=bg_secret, passphrase=bg_pass)
                                # Attempt a common account/balance call
                                # Depending on SDK version, method names differ; try a few options
                                data = None
                                for fn in ("assets", "account_assets", "get_account_assets"):
                                    if hasattr(client, fn):
                                        try:
                                            resp = getattr(client, fn)()
                                            data = resp.get("data") if isinstance(resp, dict) else resp
                                            break
                                        except Exception:
                                            continue
                                if data is None:
                                    raise RuntimeError("Bitget SDK: no se pudo obtener assets (método no encontrado)")
                                usdt_free = usdt_total = 0.0
                                usdc_free = usdc_total = 0.0
                                assets = []
                                # Normalize list of balances
                                for item in (data or []):
                                    try:
                                        ccy = str(item.get("coin") or item.get("asset") or item.get("currency") or "").upper()
                                        avail = float(item.get("available") or item.get("availableQty") or item.get("free") or 0.0)
                                        frozen = float(item.get("frozen") or item.get("locked") or 0.0)
                                        total = float(item.get("total") or (avail + frozen))
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
                                logger.info("%s balance (bitget_sdk, top 20 non-zero): %s", ex_id, ", ".join([f"{ccy}:{total}" for ccy, _free, total in top]) or "(vacío)")
                                logger.info("%s saldos (bitget_sdk): USDT free=%.8f total=%.8f | USDC free=%.8f total=%.8f", ex_id, usdt_free, usdt_total, usdc_free, usdc_total)
                                results.append({"exchange": ex_id, "assets": top, "USDT_free": usdt_free, "USDT_total": usdt_total})
                                continue
                        except Exception as e_sdk:
                            # Downgrade to info and fallback quietly
                            logger.info("%s: bitget_sdk falló (%s); usando ccxt", ex_id, e_sdk)
                    # Default ccxt path for Bitget
                    creds = {"apiKey": env.get("BITGET_API_KEY"), "secret": env.get("BITGET_API_SECRET"), "password": env.get("BITGET_PASSWORD")}
                elif ex_id == "coinbase":
                    # Coinbase Advanced requires apiKey/secret/password in ccxt
                    if not (env.get("COINBASE_API_KEY") and env.get("COINBASE_API_SECRET") and env.get("COINBASE_API_PASSWORD")):
                        logger.info("%s: sin credenciales en env (COINBASE_API_KEY/SECRET/PASSWORD)", ex_id)
                        continue
                    creds = {"apiKey": env.get("COINBASE_API_KEY"), "secret": env.get("COINBASE_API_SECRET"), "password": env.get("COINBASE_API_PASSWORD")}
                else:
                    logger.info("%s: modo balance no soportado aún", ex_id)
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
                            usdt_free = amt_free; usdt_total = amt_total
                        elif ccy_up == "USDC":
                            usdc_free = amt_free; usdc_total = amt_total
                    except Exception:
                        continue
                nonzero.sort(key=lambda x: x[2], reverse=True)
                top = nonzero[:20]
                logger.info("%s balance (top 20 non-zero): %s", ex_id, ", ".join([f"{ccy}:{total}" for ccy, _free, total in top]) or "(vacío)")
                logger.info("%s saldos (ccxt): USDT free=%.8f total=%.8f | USDC free=%.8f total=%.8f", ex_id, usdt_free, usdt_total, usdc_free, usdc_total)
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
        for it in range(1, int(max(1, args.repeat)) + 1):
            ts = pd.Timestamp.utcnow().isoformat()
            if do_console_clear:
                try:
                    if os.name == "nt":
                        os.system("cls")
                    else:
                        print("\033[2J\033[H", end="")
                except Exception:
                    pass
            iter_lines: List[str] = []
            for ex_id in EX_IDS:
                try:
                    ex = load_exchange(ex_id, args.timeout)
                    if not safe_has(ex, "fetchTickers"):
                        if ex_id != "bitso":
                            logger.warning("%s: omitido (no soporta fetchTickers para tri)", ex_id)
                        continue
                    markets = ex.load_markets()
                    tickers = ex.fetch_tickers()
                    tokens = set()
                    for s, m in markets.items():
                        if not m.get("active", True):
                            continue
                        base = m.get("base"); quote = m.get("quote")
                        if base and quote and (base == QUOTE or quote == QUOTE):
                            other = quote if base == QUOTE else base
                            if other:
                                tokens.add(other)
                    tokens = list(tokens)[: args.tri_currencies_limit]
                    fee = float(args.tri_fee)
                    opps: List[dict] = []
                    for i in range(len(tokens)):
                        X = tokens[i]
                        for j in range(len(tokens)):
                            if j == i:
                                continue
                            Y = tokens[j]
                            r1, qv1 = get_rate_and_qvol(QUOTE, X, tickers, fee, args.tri_require_topofbook)
                            if not r1:
                                continue
                            if args.tri_min_quote_vol > 0 and (qv1 is None or qv1 < args.tri_min_quote_vol):
                                continue
                            r2, qv2 = get_rate_and_qvol(X, Y, tickers, fee, args.tri_require_topofbook)
                            if not r2:
                                continue
                            if args.tri_min_quote_vol > 0 and (qv2 is None or qv2 < args.tri_min_quote_vol):
                                continue
                            r3, qv3 = get_rate_and_qvol(Y, QUOTE, tickers, fee, args.tri_require_topofbook)
                            if not r3:
                                continue
                            if args.tri_min_quote_vol > 0 and (qv3 is None or qv3 < args.tri_min_quote_vol):
                                continue
                            product = r1 * r2 * r3
                            net_pct = (product - 1.0) * 100.0
                            if net_pct >= args.tri_min_net:
                                inv_amt = float(args.inv)
                                est_after = round(inv_amt * product, 4)
                                opps.append({
                                    "exchange": ex_id,
                                    "path": f"{QUOTE}->{X}->{Y}->{QUOTE}",
                                    "r1": round(r1, 8), "r2": round(r2, 8), "r3": round(r3, 8),
                                    "net_pct": round(net_pct, 4),
                                    "inv": inv_amt,
                                    "est_after": est_after,
                                    "iteration": it,
                                    "ts": ts,
                                })
                    if opps:
                        opps.sort(key=lambda o: o["net_pct"], reverse=True)
                        lines = []
                        for o in opps[: args.tri_top]:
                            line = f"TRI@{o['exchange']} {o['path']} => net {o['net_pct']:.3f}% | {QUOTE} {o['inv']} -> {o['est_after']}"
                            lines.append(line)
                            iter_lines.append(line)
                        logger.info("== TRIANGULAR @ %s ==", ex_id)
                        logger.info("Encontradas: %d", len(opps))
                        logger.info("\n" + "\n".join(lines))
                        results.extend(opps)
                except Exception as e:
                    logger.warning("%s: triangular scan falló: %s", ex_id, e)
            # write current-only file
            try:
                # Snapshot file (last iteration only)
                with open(current_file, "w", encoding="utf-8") as fh:
                    fh.write(f"[TRI] Iteración {it}/{args.repeat} @ {ts}\n")
                    if iter_lines:
                        fh.write("\n".join(iter_lines) + "\n")
                    else:
                        fh.write("(sin oportunidades en esta iteración)\n")
                # History file (append all iterations)
                tri_hist = paths.LOGS_DIR / "tri_history.txt"
                with open(tri_hist, "a", encoding="utf-8") as fh:
                    fh.write(f"[TRI] Iteración {it}/{args.repeat} @ {ts}\n")
                    if iter_lines:
                        fh.write("\n".join(iter_lines) + "\n\n")
                    else:
                        fh.write("(sin oportunidades en esta iteración)\n\n")
            except Exception:
                pass
            if it < args.repeat:
                time.sleep(max(0.0, args.repeat_sleep))
        # save CSV
        if results:
            pd.DataFrame(results).to_csv(tri_csv, index=False)
        else:
            pd.DataFrame(columns=["exchange","path","r1","r2","r3","net_pct","inv","est_after","iteration","ts"]).to_csv(tri_csv, index=False)
        logger.info("TRI CSV: %s", tri_csv)
        return

    # -----------
    # BF MODE
    # -----------
    if args.mode == "bf":
        results_bf: List[dict] = []
    # Persistence map: (exchange, path) -> stats
        persistence: Dict[Tuple[str, str], Dict[str, object]] = {}
        paths.OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
        bf_csv = paths.OUTPUTS_DIR / f"arbitrage_bf_{QUOTE.lower()}_ccxt.csv"
        bf_persist_csv = paths.OUTPUTS_DIR / f"arbitrage_bf_{QUOTE.lower()}_persistence.csv"
        bf_sim_csv = paths.OUTPUTS_DIR / f"arbitrage_bf_simulation_{QUOTE.lower()}_ccxt.csv"
        current_file = paths.LOGS_DIR / "current_bf.txt"
    # Optional per-iteration top-k persistence CSV
    bf_top_hist_csv = paths.OUTPUTS_DIR / f"arbitrage_bf_top_{QUOTE.lower()}_history.csv"

        # Initialize simulation state (per exchange)
        sim_rows: List[dict] = []
        sim_state: Dict[str, Dict[str, object]] = {}
        if args.simulate_compound:
            for ex_id in EX_IDS:
                ccy = (allowed_quotes[0] if allowed_quotes else QUOTE)
                bal_val: float | None = None
                if args.simulate_from_wallet and creds_from_env(ex_id):
                    try:
                        ex_auth = load_exchange_auth_if_available(ex_id, args.timeout, use_auth=True)
                        bal = ex_auth.fetch_balance()
                        bucket = bal.get(args.balance_kind) or bal.get("free") or {}
                        usdt = float((bucket or {}).get("USDT") or 0.0)
                        usdc = float((bucket or {}).get("USDC") or 0.0)
                        prefer = args.simulate_prefer
                        if prefer == "auto":
                            if usdt >= usdc and usdt > 0:
                                ccy, bal_val = "USDT", usdt
                            elif usdc > 0:
                                ccy, bal_val = "USDC", usdc
                            else:
                                ccy, bal_val = ccy, 0.0
                        elif prefer == "USDT":
                            ccy, bal_val = ("USDT", usdt if usdt > 0 else usdc)
                        else:
                            ccy, bal_val = ("USDC", usdc if usdc > 0 else usdt)
                        logger.debug("Inicio desde wallet @%s: %s %.8f (prefer=%s)", ex_id, ccy, bal_val or 0.0, prefer)
                    except Exception as e:
                        # Keep warning, but remove [SIM] tag from the log line
                        logger.warning("No se pudo leer wallet @%s (%s); se usará simulate_start/--inv", ex_id, e)
                if bal_val is None:
                    bal_val = float(args.simulate_start) if args.simulate_start is not None else float(args.inv)
                # Track starting state to summarize PnL at the end
                sim_state[ex_id] = {
                    "ccy": ccy,
                    "balance": float(bal_val),
                    "start_balance": float(bal_val),
                    "start_ccy": ccy,
                }

        def bf_worker(ex_id: str, it: int, ts: str) -> Tuple[str, List[str], List[dict]]:
            local_lines: List[str] = []
            local_results: List[dict] = []
            try:
                ex = ex_instances.get(ex_id) or load_exchange_auth_if_available(ex_id, args.timeout, use_auth=bool(args.use_balance))
                if not safe_has(ex, "fetchTickers"):
                    # Silence noisy warning for exchanges like bitso that don't support fetchTickers for BF
                    if ex_id != "bitso":
                        logger.warning("%s: omitido (no soporta fetchTickers para BF)", ex_id)
                    return ex_id, local_lines, local_results
                # Markets are already loaded for cached instances; calling again keeps ccxt cache warm
                markets = ex.load_markets()
                tickers = ex.fetch_tickers()
                # Determine investment amount possibly constrained by balance
                inv_amt_cfg = float(args.inv)
                inv_amt_effective = inv_amt_cfg
                if args.use_balance:
                    bal = fetch_quote_balance(ex, QUOTE, kind=args.balance_kind)
                    if bal is not None:
                        inv_amt_effective = max(0.0, min(inv_amt_cfg, float(bal)))
                # Build currency universe around allowed anchors (e.g., USDT and USDC)
                anchors = set([q for q in allowed_quotes])
                tokens = set([q for q in anchors])
                # Build a map base -> set(quotes) to support dual-quote filtering
                base_to_quotes: Dict[str, set] = {}
                for s, m in markets.items():
                    if not m.get("active", True):
                        continue
                    base = m.get("base"); quote = m.get("quote")
                    if base and quote and (base in anchors or quote in anchors):
                        tokens.add(base); tokens.add(quote)
                    if base and quote:
                        b = str(base).upper(); q = str(quote).upper()
                        base_to_quotes.setdefault(b, set()).add(q)
                # If requested and we have 2+ anchors, restrict tokens to bases that have all anchors as quotes
                if args.bf_require_dual_quote and len(anchors) >= 2:
                    required = set(anchors)
                    filtered_tokens = set()
                    for b, qs in base_to_quotes.items():
                        if required.issubset(qs):
                            filtered_tokens.add(b)
                    # Keep anchors themselves too
                    tokens = (filtered_tokens | anchors)
                currencies = [c for c in tokens if isinstance(c, str)]
                # Optionally rank currencies by aggregate quote volume (desc) to prioritize liquid markets
                if args.bf_rank_by_qvol and markets and isinstance(tickers, dict):
                    qvol_by_ccy: Dict[str, float] = {}
                    for sym, t in tickers.items():
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
                    currencies = sorted(currencies, key=lambda c: qvol_by_ccy.get(c, 0.0), reverse=True)
                currencies = currencies[: max(1, args.bf_currencies_limit)]
                if args.bf_debug:
                    try:
                        logger.info("[BF-DBG] %s currencies=%d (anchors=%s)", ex_id, len(currencies), ','.join(sorted(anchors)))
                    except Exception:
                        logger.info("[BF-DBG] %s currencies=%d", ex_id, len(currencies))
                # Ensure at least one anchor is at front for consistency
                for q in allowed_quotes:
                    if q in currencies:
                        currencies = [q] + [c for c in currencies if c != q]
                        break
                edges, rate_map = build_rates_for_exchange(
                    currencies, tickers, args.bf_fee,
                    require_topofbook=args.bf_require_topofbook,
                    min_quote_vol=args.bf_min_quote_vol,
                )
                if args.bf_debug:
                    logger.info("[BF-DBG] %s edges=%d", ex_id, len(edges))
                n = len(currencies)
                if n < 3 or not edges:
                    return ex_id, local_lines, local_results
                dist = [0.0] * n
                pred = [-1] * n
                for _ in range(n - 1):
                    updated = False
                    for (u, v, w) in edges:
                        if dist[u] + w < dist[v] - 1e-12:
                            dist[v] = dist[u] + w
                            pred[v] = u
                            updated = True
                    if not updated:
                        break
                cycles_found = 0
                seen_cycles: set[tuple[str, ...]] = set()
                for (u, v, w) in edges:
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
                        # Require cycle to include at least one allowed anchor when requested
                        if len(cycle_nodes) < 2 or (args.bf_require_quote and not any(q in cycle_nodes for q in allowed_quotes)):
                            continue
                        cycle_nodes = list(reversed(cycle_nodes))
                        # Rotate to start at an allowed anchor if present
                        chosen_anchor_idx = None
                        for q in allowed_quotes:
                            if q in cycle_nodes:
                                chosen_anchor_idx = cycle_nodes.index(q)
                                break
                        if chosen_anchor_idx is not None:
                            cycle_nodes = cycle_nodes[chosen_anchor_idx:] + cycle_nodes[:chosen_anchor_idx]
                        key = tuple(cycle_nodes)
                        if key in seen_cycles:
                            continue
                        seen_cycles.add(key)
                        prod = 1.0
                        valid = True
                        for i in range(len(cycle_nodes) - 1):
                            a = cycle_nodes[i]; b = cycle_nodes[i + 1]
                            u_i = currencies.index(a); v_i = currencies.index(b)
                            rate = rate_map.get((u_i, v_i))
                            if rate is None or rate <= 0:
                                valid = False
                                break
                            prod *= rate
                        if valid and cycle_nodes[0] != cycle_nodes[-1]:
                            a = cycle_nodes[-1]; b = cycle_nodes[0]
                            u_i = currencies.index(a); v_i = currencies.index(b)
                            rate = rate_map.get((u_i, v_i))
                            if rate is None or rate <= 0:
                                valid = False
                            else:
                                prod *= rate
                                cycle_nodes.append(cycle_nodes[0])
                        if not valid:
                            continue
                        hops = len(cycle_nodes) - 1
                        if (args.bf_min_hops and hops < args.bf_min_hops) or (args.bf_max_hops and hops > args.bf_max_hops):
                            continue
                        net_pct = (prod - 1.0) * 100.0
                        # Enforce overall and per-hop quality thresholds
                        if net_pct < args.bf_min_net:
                            continue
                        if args.bf_min_net_per_hop and (net_pct / max(1, hops)) < float(args.bf_min_net_per_hop):
                            continue
                        inv_amt = float(inv_amt_effective)
                        est_after = round(inv_amt * prod, 4)
                        path_str = "->".join(cycle_nodes)
                        bal_suffix = ""
                        if args.use_balance and inv_amt_effective != inv_amt_cfg:
                            bal_suffix = f" (saldo usado {QUOTE} {inv_amt_effective:.2f} de {inv_amt_cfg:.2f})"
                        msg = f"BF@{ex_id} {path_str} ({hops}hops) => net {net_pct:.3f}% | {QUOTE} {inv_amt:.2f} -> {est_after:.4f}{bal_suffix}"
                        logger.info(msg)
                        local_lines.append(msg)
                        local_results.append({
                            "exchange": ex_id,
                            "path": path_str,
                            "net_pct": round(net_pct, 4),
                            "inv": inv_amt,
                            "est_after": est_after,
                            "hops": hops,
                            "iteration": it,
                            "ts": ts,
                        })
                        cycles_found += 1
                        if cycles_found >= args.bf_top:
                            break
                if args.bf_debug:
                    logger.info("[BF-DBG] %s cycles_found=%d (min_net=%.3f%%)", ex_id, cycles_found, args.bf_min_net)
                time.sleep(args.sleep)
            except Exception as e:
                logger.warning("%s: BF scan falló: %s", ex_id, e)
            return ex_id, local_lines, local_results

        for it in range(1, int(max(1, args.repeat)) + 1):
            ts = pd.Timestamp.utcnow().isoformat()
            if do_console_clear:
                try:
                    if os.name == "nt":
                        os.system("cls")
                    else:
                        print("\033[2J\033[H", end="")
                except Exception:
                    pass
            iter_lines: List[str] = []
            iter_results: List[dict] = []
            # Run workers (threaded or sequential)
            # If --bf_threads <= 0, use one thread per exchange. Otherwise, limit to the number of exchanges.
            configured_threads = int(args.bf_threads)
            num_workers = len(EX_IDS) if configured_threads <= 0 else min(configured_threads, len(EX_IDS))
            if max(1, num_workers) > 1:
                with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, num_workers)) as pool:
                    futures = [pool.submit(bf_worker, ex_id, it, ts) for ex_id in EX_IDS]
                    for fut in concurrent.futures.as_completed(futures):
                        ex_id, lines, rows = fut.result()
                        iter_lines.extend(lines)
                        # persistence update must be synchronized; here it's single-threaded in main
                        for row in rows:
                            iter_results.append(row)
                            key = (row["exchange"], row["path"])
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
                                st["occurrences"] = int(st.get("occurrences", 0)) + 1
                                prev_it = int(st.get("last_it", 0))
                                if prev_it + 1 == it:
                                    st["current_streak"] = int(st.get("current_streak", 0)) + 1
                                else:
                                    st["current_streak"] = 1
                                st["max_streak"] = max(int(st.get("max_streak", 0)), int(st.get("current_streak", 0)))
                                st["last_it"] = it
                            results_bf.append(row)
            else:
                for ex_id in EX_IDS:
                    _ex_id, lines, rows = bf_worker(ex_id, it, ts)
                    iter_lines.extend(lines)
                    for row in rows:
                        iter_results.append(row)
                        key = (row["exchange"], row["path"])
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
                            st["occurrences"] = int(st.get("occurrences", 0)) + 1
                            prev_it = int(st.get("last_it", 0))
                            if prev_it + 1 == it:
                                st["current_streak"] = int(st.get("current_streak", 0)) + 1
                            else:
                                st["current_streak"] = 1
                            st["max_streak"] = max(int(st.get("max_streak", 0)), int(st.get("current_streak", 0)))
                            st["last_it"] = it
                        results_bf.append(row)

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
                        def start_end_with_ccy(r: dict, c: str) -> bool:
                            try:
                                parts = str(r.get("path") or "").split("->")
                                return len(parts) >= 2 and parts[0].upper() == c.upper() and parts[-1].upper() == c.upper()
                            except Exception:
                                return False
                        # Best per anchor for this exchange
                        best_per_anchor: Dict[str, dict] = {}
                        anchors_iter = set([a for a in allowed_quotes]) if allowed_quotes else {QUOTE}
                        for anc in anchors_iter:
                            anc_cands = [r for r in rows_ex if start_end_with_ccy(r, anc)]
                            if not anc_cands:
                                continue
                            if args.simulate_select == "first":
                                best_per_anchor[anc] = anc_cands[0]
                            else:
                                best_per_anchor[anc] = max(anc_cands, key=lambda r: float(r.get("net_pct", 0.0)))
                        current_best = best_per_anchor.get(ccy)
                        chosen_anchor = ccy
                        chosen_row = current_best
                        if args.simulate_auto_switch and best_per_anchor:
                            overall_anchor, overall_row = None, None
                            for anc, row in best_per_anchor.items():
                                if overall_row is None or float(row.get("net_pct", 0.0)) > float(overall_row.get("net_pct", 0.0)):
                                    overall_anchor, overall_row = anc, row
                            if overall_row is not None:
                                cur_net = float(current_best.get("net_pct", 0.0)) if current_best else -1e9
                                over_net = float(overall_row.get("net_pct", 0.0))
                                if current_best is None or (over_net - cur_net) >= float(args.simulate_switch_threshold) - 1e-12:
                                    chosen_anchor, chosen_row = overall_anchor, overall_row
                        if chosen_row is not None:
                            if chosen_anchor != ccy:
                                # Anchor change is useful but keep it silent at INFO level to avoid [SIM] duplication
                                logger.debug("Cambio de ancla @%s: %s -> %s (mejor net%%)", ex_id, ccy, chosen_anchor)
                                ccy = chosen_anchor
                            selected = chosen_row
                    if selected is not None:
                        product = 1.0 + (float(selected.get("net_pct", 0.0)) / 100.0)
                        before = balance
                        after = round(before * product, 8)
                        gain_amt = round(after - before, 8)
                        gain_pct = round((product - 1.0) * 100.0, 6)
                        sim_rows.append({
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
                        })
                        # Update state
                        sim_state[ex_id] = {"ccy": ccy, "balance": after}
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
                            df_top = df_top.sort_values("net_pct", ascending=False).head(max(1, int(args.bf_top)))
                            header = not os.path.exists(bf_top_hist_csv)
                            df_top.to_csv(bf_top_hist_csv, mode="a", header=header, index=False)
                    except Exception:
                        pass
                # Snapshot file (last iteration only)
                with open(current_file, "w", encoding="utf-8") as fh:
                    fh.write(f"[BF] Iteración {it}/{args.repeat} @ {ts}\n")
                    if iter_lines:
                        fh.write("\n".join(iter_lines) + "\n")
                    else:
                        fh.write("(sin oportunidades en esta iteración)\n")
                # History file (append all iterations)
                bf_hist = paths.LOGS_DIR / "bf_history.txt"
                with open(bf_hist, "a", encoding="utf-8") as fh:
                    fh.write(f"[BF] Iteración {it}/{args.repeat} @ {ts}\n")
                    if iter_lines:
                        fh.write("\n".join(iter_lines) + "\n\n")
                    else:
                        fh.write("(sin oportunidades en esta iteración)\n\n")
            except Exception:
                pass
            if it < args.repeat:
                time.sleep(max(0.0, args.repeat_sleep))
        if results_bf:
            pd.DataFrame(results_bf).to_csv(bf_csv, index=False)
        else:
            pd.DataFrame(columns=["exchange","path","net_pct","inv","est_after","hops","iteration","ts"]).to_csv(bf_csv, index=False)
            logger.info(
                "BF: sin oportunidades con los filtros actuales (min_net=%s%%, require_topofbook=%s, min_quote_vol=%s). Prueba relajar filtros (p.ej. bajar --bf_min_quote_vol, quitar --bf_require_topofbook, o bajar --bf_min_net) o aumentar --bf_currencies_limit.",
                args.bf_min_net, bool(args.bf_require_topofbook), args.bf_min_quote_vol,
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
                        start_bal = float(st.get("start_balance", st.get("balance", 0.0)) or 0.0)
                    except Exception:
                        start_bal = 0.0
                    try:
                        end_bal = float(st.get("balance", 0.0) or 0.0)
                    except Exception:
                        end_bal = 0.0
                    ccy = str(st.get("ccy") or QUOTE)
                    start_ccy = str(st.get("start_ccy") or ccy)
                    roi_pct = ( (end_bal - start_bal) / start_bal * 100.0 ) if start_bal > 0 else None
                    summary_rows.append({
                        "exchange": ex_id,
                        "start_currency": start_ccy,
                        "start_balance": round(start_bal, 8),
                        "end_currency": ccy,
                        "end_balance": round(end_bal, 8),
                        "roi_pct": None if roi_pct is None else round(roi_pct, 6),
                        "iterations": int(max(1, args.repeat)),
                    })
                bf_sim_summary_csv = paths.OUTPUTS_DIR / f"arbitrage_bf_simulation_summary_{QUOTE.lower()}_ccxt.csv"
                pd.DataFrame(summary_rows).to_csv(bf_sim_summary_csv, index=False)
                # Log a short summary line per exchange (sorted by ROI desc)
                try:
                    rows_sorted = sorted(summary_rows, key=lambda r: (r["roi_pct"] if r["roi_pct"] is not None else float("-inf")), reverse=True)
                except Exception:
                    rows_sorted = summary_rows
                for r in rows_sorted:
                    roi_txt = "N/A" if r["roi_pct"] is None else f"{r['roi_pct']:.4f}%"
                    logger.info("BF SIM SUM @%s: %s %.4f -> %s %.4f (ROI %s, it=%d)",
                                r["exchange"], r["start_currency"], r["start_balance"],
                                r["end_currency"], r["end_balance"], roi_txt, r["iterations"])
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
                rows.append({
                    "exchange": ex_id,
                    "path": path_str,
                    "first_seen": st.get("first_seen"),
                    "last_seen": st.get("last_seen"),
                    "occurrences": st.get("occurrences"),
                    "max_streak": st.get("max_streak"),
                    "approx_duration_s": approx_duration_s,
                })
            pd.DataFrame(rows).to_csv(bf_persist_csv, index=False)
            logger.info("BF Persistence CSV: %s", bf_persist_csv)
        return

    # ---------------------------
    # INTER-EXCHANGE SPREAD MODE
    # ---------------------------
    paths.OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    # 1) Build per-exchange universe of symbols with given QUOTE
    bases_ordered: List[str] = []
    symbols_per_ex: Dict[str, List[str]] = {}
    for ex_id in EX_IDS:
        try:
            ex = load_exchange(ex_id, args.timeout)
            if not safe_has(ex, "fetchTicker"):
                if ex_id != "bitso":
                    logger.warning("%s: omitido (no soporta fetchTicker público)", ex_id)
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

    bases_ordered = bases_ordered[: UNIVERSE_LIMIT]
    target_symbols = [f"{b}/{QUOTE}" for b in bases_ordered]

    current_file = paths.LOGS_DIR / "current_inter.txt"
    for it in range(1, int(max(1, args.repeat)) + 1):
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
                            rows.append({
                                "exchange": ex_id,
                                "symbol": sym,
                                "base": sym.split("/")[0],
                                "bid": float(bid),
                                "ask": float(ask),
                                "qvol": qvol,
                            })
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
                            rows.append({
                                "exchange": ex_id,
                                "symbol": sym,
                                "base": sym.split("/")[0],
                                "bid": float(bid),
                                "ask": float(ask),
                                "qvol": qvol,
                            })
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
            buy_idx = g["ask"].idxmin(); sell_idx = g["bid"].idxmax()
            if pd.isna(buy_idx) or pd.isna(sell_idx):
                continue
            buy_row = g.loc[buy_idx]; sell_row = g.loc[sell_idx]
            if sell_row["bid"] <= 0 or buy_row["ask"] <= 0:
                continue
            base_token = str(buy_row["base"]).upper()
            if not args.include_stables and base_token in STABLE_BASES:
                continue
            if args.min_price > 0.0 and (buy_row["ask"] < args.min_price or sell_row["bid"] < args.min_price):
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
                out_rows.append({
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
                })

        report = pd.DataFrame(out_rows)
        had_symbols = set(df["symbol"].unique())
        opp_symbols = set(report["symbol"].unique()) if not report.empty else set()
        no_opp_symbols = sorted(had_symbols - opp_symbols)

        if not report.empty:
            report.sort_values(["est_net_pct", "gross_spread_pct"], ascending=[False, False], inplace=True)

        csv_opp = paths.OUTPUTS_DIR / f"arbitrage_report_{QUOTE.lower()}_ccxt.csv"
        csv_no = paths.OUTPUTS_DIR / f"arbitrage_report_{QUOTE.lower()}_ccxt_noop.csv"
        if not report.empty:
            report.to_csv(csv_opp, index=False)
        else:
            pd.DataFrame(columns=[
                "symbol","base","buy_exchange","buy_price","sell_exchange","sell_price",
                "gross_spread_pct","est_net_pct","sources","gross_profit_amt","net_profit_amt",
            ]).to_csv(csv_opp, index=False)
        pd.DataFrame({"symbol": no_opp_symbols}).to_csv(csv_no, index=False)

        logger.info("== ARBITRAGE_REPORT_CCXT ==")
        logger.info(
            "Oportunidades: %d | Sin oportunidad: %d | Total símbolos: %d",
            0 if report.empty else len(report), len(no_opp_symbols), len(had_symbols),
        )
        lines: List[str] = []
        disclaimer = " [nota: datos multi-exchange; puede incluir venues no confiables o ilíquidos]" if args.ex.strip().lower() == "all" else ""
        for _, r in report.head(args.top).iterrows():
            buy_p = fmt_price(float(r["buy_price"]))
            sell_p = fmt_price(float(r["sell_price"]))
            lines.append(
                f"{r['symbol']} => BUY@{r['buy_exchange']} {buy_p} → "
                f"SELL@{r['sell_exchange']} {sell_p} "
                f"(gross {r['gross_spread_pct']:.3f}% | net {r['est_net_pct']:.3f}%)" + disclaimer
            )
        if lines:
            logger.info("\n" + "\n".join(lines))
        logger.info("\n%s", tabulate(report.head(args.top), headers="keys", tablefmt="github", showindex=False))
        logger.info("CSV: %s", csv_opp)
        logger.info(
            "Params: quote=%s max=%d min_spread=%s%% fees(buy/sell)=%s%%/%s%% xfer=%s%% exchanges=%s",
            QUOTE, UNIVERSE_LIMIT, args.min_spread, args.buy_fee, args.sell_fee, args.xfer_fee_pct, ",".join(EX_IDS),
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
            # History file (append all iterations)
            inter_hist = paths.LOGS_DIR / "inter_history.txt"
            with open(inter_hist, "a", encoding="utf-8") as fh:
                fh.write(f"[INTER] Iteración {it}/{args.repeat} @ {now_ts}\n")
                if lines:
                    fh.write("\n".join(lines) + "\n\n")
                else:
                    fh.write("(sin oportunidades en esta iteración)\n\n")
        except Exception:
            pass
        if it < args.repeat:
            time.sleep(max(0.0, args.repeat_sleep))


if __name__ == "__main__":
    main()
