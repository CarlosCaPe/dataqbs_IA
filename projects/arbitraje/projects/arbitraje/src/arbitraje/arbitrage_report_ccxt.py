
# Shim wrapper to delegate to canonical implementation to avoid duplicated source.
# The real implementation lives at:
#   projects/arbitraje/src/arbitraje/arbitrage_report_ccxt.py
# This shim dynamically loads that file and re-exports its symbols so either
# path (the nested one or the canonical one) behaves the same. This keeps the
# repository consistent and avoids drift between copies.
import importlib.util
import sys
from pathlib import Path

# Robust relative resolution: walk parents and try likely candidate locations for the
# canonical implementation. This avoids absolute paths so the shim works across
# checkouts regardless of the filesystem root.
_CANONICAL_FILE = None
_self = Path(__file__).resolve()
for p in ([_self] + list(_self.parents)):
    # Candidate 1: repository-root/projects/arbitraje/src/arbitraje/...
    cand = p / "projects" / "arbitraje" / "src" / "arbitraje" / "arbitrage_report_ccxt.py"
    if cand.exists():
        _CANONICAL_FILE = cand.resolve()
        break
    # Candidate 2: repository-root/src/arbitraje/...
    cand2 = p / "src" / "arbitraje" / "arbitrage_report_ccxt.py"
    if cand2.exists():
        _CANONICAL_FILE = cand2.resolve()
        break

if _CANONICAL_FILE is None:
    raise FileNotFoundError(
        "Could not locate canonical 'arbitrage_report_ccxt.py' from shim;"
        " expected under projects/arbitraje/src/arbitraje or src/arbitraje"
    )

spec = importlib.util.spec_from_file_location("arbitrage_report_ccxt_canonical", str(_CANONICAL_FILE))
module = importlib.util.module_from_spec(spec)
sys.modules["arbitrage_report_ccxt_canonical"] = module
try:
    spec.loader.exec_module(module)  # type: ignore[attr-defined]
except Exception:
    # Re-raise to keep traceback for easier debugging
    raise

# Re-export public names so imports like `from arbitrage.arbitrage_report_ccxt import main`
# continue to work when referencing the nested path.
for _name in dir(module):
    if _name.startswith("__"):
        continue
    try:
        globals()[_name] = getattr(module, _name)
    except Exception:
        # Non-critical: skip attributes that can't be copied
        pass

if __name__ == "__main__":
    if hasattr(module, "main"):
        module.main()
    else:
        raise RuntimeError("Canonical module does not expose main()")
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

    swaps_blacklist_map: Dict[str, set[str]] = load_swaps_blacklist()

    # Pre-create and cache ccxt exchange instances (and markets) to speed up repeated iterations
    ex_instances: Dict[str, ccxt.Exchange] = {}
    try:
        preload_for_modes = {"bf", "tri"}
        if args.mode in preload_for_modes:
            for _ex in EX_IDS:
                try:
                    inst = load_exchange_auth_if_available(_ex, args.timeout, use_auth=bool(creds_from_env(_ex)))
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
                            logger.info("%s balance (native, top 20 non-zero): %s", ex_id, ", ".join([f"{ccy}:{total}" for ccy, _free, total in top]) or "(vac├¡o)")
                            logger.info("%s saldos (native): USDT free=%.8f total=%.8f | USDC free=%.8f total=%.8f", ex_id, usdt_free, usdt_total, usdc_free, usdc_total)
                            results.append({"exchange": ex_id, "assets": top})
                            continue
                        except Exception as e:
                            logger.warning("%s: native balance fall├│: %s; fallback a ccxt", ex_id, e)
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
                            logger.info("%s balance (connector, top 20 non-zero): %s", ex_id, ", ".join([f"{ccy}:{total}" for ccy, _free, total in top]) or "(vac├¡o)")
                            logger.info("%s saldos (connector): USDT free=%.8f total=%.8f | USDC free=%.8f total=%.8f", ex_id, usdt_free, usdt_total, usdc_free, usdc_total)
                            results.append({"exchange": ex_id, "assets": top, "USDT_free": usdt_free, "USDT_total": usdt_total})
                            continue
                        except Exception as e:
                            logger.warning("%s: connector balance fall├│: %s; fallback a ccxt", ex_id, e)
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
                                    raise RuntimeError("Bitget SDK: no se pudo obtener assets (m├⌐todo no encontrado)")
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
                                logger.info("%s balance (bitget_sdk, top 20 non-zero): %s", ex_id, ", ".join([f"{ccy}:{total}" for ccy, _free, total in top]) or "(vac├¡o)")
                                logger.info("%s saldos (bitget_sdk): USDT free=%.8f total=%.8f | USDC free=%.8f total=%.8f", ex_id, usdt_free, usdt_total, usdc_free, usdc_total)
                                results.append({"exchange": ex_id, "assets": top, "USDT_free": usdt_free, "USDT_total": usdt_total})
                                continue
                        except Exception as e_sdk:
                            # Downgrade to info and fallback quietly
                            logger.info("%s: bitget_sdk fall├│ (%s); usando ccxt", ex_id, e_sdk)
                    # Default ccxt path for Bitget
                    creds = {"apiKey": env.get("BITGET_API_KEY"), "secret": env.get("BITGET_API_SECRET"), "password": env.get("BITGET_PASSWORD")}
                elif ex_id == "coinbase":
                    # Coinbase Advanced requires apiKey/secret/password in ccxt
                    if not (env.get("COINBASE_API_KEY") and env.get("COINBASE_API_SECRET") and env.get("COINBASE_API_PASSWORD")):
                        logger.info("%s: sin credenciales en env (COINBASE_API_KEY/SECRET/PASSWORD)", ex_id)
                        continue
                    creds = {"apiKey": env.get("COINBASE_API_KEY"), "secret": env.get("COINBASE_API_SECRET"), "password": env.get("COINBASE_API_PASSWORD")}
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
                            usdt_free = amt_free; usdt_total = amt_total
                        elif ccy_up == "USDC":
                            usdc_free = amt_free; usdc_total = amt_total
                    except Exception:
                        continue
                nonzero.sort(key=lambda x: x[2], reverse=True)
                top = nonzero[:20]
                logger.info("%s balance (top 20 non-zero): %s", ex_id, ", ".join([f"{ccy}:{total}" for ccy, _free, total in top]) or "(vac├¡o)")
                logger.info("%s saldos (ccxt): USDT free=%.8f total=%.8f | USDC free=%.8f total=%.8f", ex_id, usdt_free, usdt_total, usdc_free, usdc_total)
                results.append({"exchange": ex_id, "assets": top})
            except Exception as e:
                logger.warning("%s: fetch_balance fall├│: %s", ex_id, e)
        return

    # ---------------
    # TRIANGULAR MODE
    # ---------------
    if args.mode == "tri":
        results: List[dict] = []
        paths.OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
        tri_csv = paths.OUTPUTS_DIR / f"arbitrage_tri_{QUOTE.lower()}_ccxt.csv"
        current_file = paths.LOGS_DIR / "current_tri.txt"
        tri_iter_csv = paths.OUTPUTS_DIR / f"arbitrage_tri_current_{QUOTE.lower()}_ccxt.csv"
        for it in range(1, int(max(1, args.repeat)) + 1):
            ts = pd.Timestamp.utcnow().isoformat()
            swaps_blacklist_map = load_swaps_blacklist()
            # Prefetch wallet balances once per iteration (optional)
            wallet_buckets_cache: Dict[str, Dict[str, float]] = {}
            try:
                if args.simulate_compound and getattr(args, "simulate_from_wallet", False):
                    wallet_buckets_cache = _prefetch_wallet_buckets(list(EX_IDS), args)
            except Exception:
                wallet_buckets_cache = {}
            # Hydrate simulation balances from wallet snapshot exactly once (first iteration only)
            try:
                if args.simulate_compound and getattr(args, "simulate_from_wallet", False) and it == 1 and wallet_buckets_cache:
                    for ex_id in EX_IDS:
                        st = sim_state.get(ex_id)
                        if not st:
                            continue
                        wb = wallet_buckets_cache.get(ex_id) or {}
                        usdt = float(wb.get("USDT", 0.0) or 0.0)
                        usdc = float(wb.get("USDC", 0.0) or 0.0)
                        prefer = str(getattr(args, "simulate_prefer", "auto") or "auto").upper()
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
                                chosen_ccy, chosen_bal = chosen_ccy, 0.0
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
            # Also clean snapshot alias file
            try:
                current_alias = paths.LOGS_DIR / "CURRENT_BF.txt"
                if current_alias.exists():
                    current_alias.unlink()  # type: ignore[arg-type]
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
                            logger.warning("%s: omitido (no soporta fetchTickers para tri)", ex_id)
                        continue
                    markets = ex.load_markets()
                    tickers = ex.fetch_tickers()
                    ex_norm = normalize_ccxt_id(ex_id)
                    exchange_blacklist = swaps_blacklist_map.get(ex_norm, set())
                    tokens = set()
                    for s, m in markets.items():
                        if not m.get("active", True):
                            continue
                        base = str(m.get("base") or "").upper(); quote = str(m.get("quote") or "").upper()
                        if base and quote and (base == QUOTE or quote == QUOTE):
                            other = quote if base == QUOTE else base
                            if other:
                                tokens.add(str(other).upper())
                    tokens = [t for t in list(tokens) if isinstance(t, str)]
                    if exchange_blacklist:
                        tokens = [t for t in tokens if not _pair_is_blacklisted(exchange_blacklist, QUOTE, t)]
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
                            if _pair_is_blacklisted(exchange_blacklist, Y, QUOTE):
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
                        iter_results.extend(opps)
                except Exception as e:
                    logger.warning("%s: triangular scan fall├│: %s", ex_id, e)
            # write current-only file
            try:
                # Overwrite current-iteration CSV
                try:
                    if iter_results:
                        pd.DataFrame(iter_results).to_csv(tri_iter_csv, index=False)
                    else:
                        pd.DataFrame(columns=["exchange","path","r1","r2","r3","net_pct","inv","est_after","iteration","ts"]).to_csv(tri_iter_csv, index=False)
                except Exception:
                    pass
                # Snapshot file (last iteration only)
                with open(current_file, "w", encoding="utf-8") as fh:
                    fh.write(f"[TRI] Iteraci├│n {it}/{args.repeat} @ {ts}\n")
                    if iter_lines:
                        fh.write("\n".join(iter_lines) + "\n")
                    else:
                        fh.write("(sin oportunidades en esta iteraci├│n)\n")
                # History file (overwrite per iteration)
                tri_hist = paths.LOGS_DIR / "tri_history.txt"
                with open(tri_hist, "w", encoding="utf-8") as fh:
                    fh.write(f"[TRI] Iteraci├│n {it}/{args.repeat} @ {ts}\n")
                    if iter_lines:
                        fh.write("\n".join(iter_lines) + "\n\n")
                    else:
                        fh.write("(sin oportunidades en esta iteraci├│n)\n\n")
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
        # Use lowercase snapshot filename consistently with repo conventions
        current_file = paths.LOGS_DIR / "current_bf.txt"
        # Optional per-iteration top-k persistence CSV
        bf_top_hist_csv = paths.OUTPUTS_DIR / f"arbitrage_bf_top_{QUOTE.lower()}_history.csv"
        # Per-iteration snapshot CSV (overwritten each iteration)
        bf_iter_csv = paths.OUTPUTS_DIR / f"arbitrage_bf_current_{QUOTE.lower()}_ccxt.csv"

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
        sim_state: Dict[str, Dict[str, object]] = {}
        if args.simulate_compound:
            for ex_id in EX_IDS:
                # Default anchor choice
                default_ccy = (allowed_quotes[0] if allowed_quotes else QUOTE)
                ccy = default_ccy
                bal_val: float | None = None
                if args.simulate_from_wallet:
                    # Honor simulate_prefer for currency selection even if balance is 0
                    prefer = args.simulate_prefer
                    if prefer == "USDT":
                        ccy = "USDT"
                    elif prefer == "USDC":
                        ccy = "USDC"
                    # Attempt to read wallet only if we have creds
                    if creds_from_env(ex_id):
                        try:
                            ex_auth = load_exchange_auth_if_available(ex_id, args.timeout, use_auth=True)
                            bal = ex_auth.fetch_balance()
                            bucket = bal.get("free") or {}
                            usdt = float((bucket or {}).get("USDT") or 0.0)
                            usdc = float((bucket or {}).get("USDC") or 0.0)
                            if prefer == "auto":
                                if usdt >= usdc and usdt > 0:
                                    ccy, bal_val = "USDT", usdt
                                elif usdc > 0:
                                    ccy, bal_val = "USDC", usdc
                                else:
                                    # No balance in anchors; keep current ccy but start from 0
                                    bal_val = 0.0
                            elif prefer == "USDT":
                                ccy, bal_val = ("USDT", usdt if usdt > 0 else 0.0)
                            else:
                                ccy, bal_val = ("USDC", usdc if usdc > 0 else 0.0)
                            logger.debug("Inicio desde wallet @%s: %s %.8f (prefer=%s)", ex_id, ccy, bal_val or 0.0, prefer)
                        except Exception as e:
                            # Balance requested but unavailable: initialize with 0
                            logger.warning("No se pudo leer wallet @%s (%s); saldo inicial 0.0", ex_id, e)
                            bal_val = 0.0
                    else:
                        # No credentials: treat as unavailable wallet
                        bal_val = 0.0
                # Fallback only when not using wallet-based start
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
                ex = ex_instances.get(ex_id) or load_exchange_auth_if_available(ex_id, args.timeout, use_auth=bool(creds_from_env(ex_id)))
                if not getattr(ex, "apiKey", None):
                    ex = load_exchange_auth_if_available(ex_id, args.timeout, use_auth=True)
                if not safe_has(ex, "fetchTickers"):
                    # Silence noisy warning for exchanges like bitso that don't support fetchTickers for BF
                    if ex_id != "bitso":
                        logger.warning("%s: omitido (no soporta fetchTickers para BF)", ex_id)
                    return ex_id, local_lines, local_results
                # Markets are already loaded for cached instances; calling again keeps ccxt cache warm
                markets = ex.load_markets()
                tickers = ex.fetch_tickers()
                ex_norm = normalize_ccxt_id(ex_id)
                exchange_blacklist = swaps_blacklist_map.get(ex_norm, set())
                if args.bf_debug and exchange_blacklist:
                    logger.info("[BF-DBG] %s blacklist_pairs=%d", ex_id, len(exchange_blacklist))
                # Determine investment amount possibly constrained by balance
                inv_amt_cfg = float(args.inv)
                inv_amt_effective = inv_amt_cfg
                bal = fetch_quote_balance(ex, QUOTE, kind="free")
                if bal is not None:
                    bal_f = max(0.0, float(bal))
                    if inv_amt_cfg <= 0.0:
                        inv_amt_effective = bal_f
                    else:
                        inv_amt_effective = max(0.0, min(inv_amt_cfg, bal_f))
                else:
                    inv_amt_effective = max(0.0, inv_amt_cfg)
                # Build currency universe around allowed anchors (e.g., USDT and USDC)
                anchors = set([q for q in allowed_quotes])
                currencies: List[str] | None = None
                # Micro-cache when qvol ranking is OFF
                if not args.bf_rank_by_qvol:
                    cache_key = (
                        ex_id,
                        int(args.bf_currencies_limit),
                        bool(args.bf_require_dual_quote),
                        tuple(sorted(list(anchors))),
                    )
                    try:
                        currencies = _currencies_cache.get(cache_key)  # type: ignore[name-defined]
                    except Exception:
                        currencies = None
                if not currencies:
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
                    if not args.bf_rank_by_qvol:
                        currencies = currencies[: max(1, args.bf_currencies_limit)]
                        for q in allowed_quotes:
                            if q in currencies:
                                currencies = [q] + [c for c in currencies if c != q]
                                break
                        try:
                            _currencies_cache[cache_key] = list(currencies)  # type: ignore[name-defined]
                        except Exception:
                            pass
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
                # If ranking path was taken, apply limit and ensure anchor-first
                if args.bf_rank_by_qvol:
                    currencies = currencies[: max(1, args.bf_currencies_limit)]
                    for q in allowed_quotes:
                        if q in currencies:
                            currencies = [q] + [c for c in currencies if c != q]
                            break
                if args.bf_debug:
                    try:
                        logger.info("[BF-DBG] %s currencies=%d (anchors=%s)", ex_id, len(currencies), ','.join(sorted(anchors)))
                    except Exception:
                        logger.info("[BF-DBG] %s currencies=%d", ex_id, len(currencies))
                # Note: anchor-first applied above in ranking path or via cache otherwise
                edges, rate_map = build_rates_for_exchange(
                    currencies, tickers, args.bf_fee,
                    require_topofbook=args.bf_require_topofbook,
                    min_quote_vol=args.bf_min_quote_vol,
                    blacklisted_symbols=exchange_blacklist,
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
                        # Optional depth-aware revalidation for more realistic net%
                        used_ws_flag = False
                        slip_bps = 0.0
                        fee_bps_total = float(args.bf_fee) * hops
                        net_pct_adj = net_pct
                        if args.bf_revalidate_depth:
                            try:
                                net_pct2, fee_bps_total2, slip_bps2, used_ws_flag2 = _bf_revalidate_cycle_with_depth(
                                    ex,
                                    cycle_nodes=list(cycle_nodes),
                                    inv_quote=inv_amt,
                                    fee_bps_per_hop=float(args.bf_fee),
                                    depth_levels=int(args.bf_depth_levels),
                                    use_ws=bool(args.bf_use_ws),
                                    latency_penalty_bps=float(args.bf_latency_penalty_bps),
                                )
                                if net_pct2 is not None:
                                    net_pct_adj = float(net_pct2)
                                    fee_bps_total = float(fee_bps_total2)
                                    slip_bps = float(slip_bps2)
                                    used_ws_flag = bool(used_ws_flag2)
                                    est_after = round(inv_amt * (1.0 + net_pct_adj/100.0), 6)
                                    # Enforce thresholds again using adjusted net
                                    if net_pct_adj < float(args.bf_min_net):
                                        continue
                                    if args.bf_min_net_per_hop and (net_pct_adj / max(1, hops)) < float(args.bf_min_net_per_hop):
                                        continue
                                else:
                                    # If revalidation requested but no adjusted value, skip to be conservative
                                    continue
                            except Exception:
                                pass
                        path_str = "->".join(cycle_nodes)
                        if exchange_blacklist:
                            path_pairs = _expand_path_to_pairs(path_str)
                            if any(p in exchange_blacklist for p in path_pairs):
                                if args.bf_debug:
                                    logger.info("[BF-DBG] %s omitiendo ciclo en blacklist: %s", ex_id, path_str)
                                continue
                        # Remove noisy balance suffix per user request
                        bal_suffix = ""
                        if args.bf_revalidate_depth:
                            msg = (
                                f"BF@{ex_id} {path_str} ({hops}hops) => net {net_pct_adj:.3f}% (raw {net_pct:.3f}%, slip {slip_bps:.1f}bps, fee {fee_bps_total:.1f}bps"
                                f"{' +ws' if used_ws_flag else ''}) | {QUOTE} {inv_amt:.2f} -> {est_after:.6f}"
                            )
                        else:
                            msg = f"BF@{ex_id} {path_str} ({hops}hops) => net {net_pct:.3f}% | {QUOTE} {inv_amt:.2f} -> {est_after:.4f}"
                        logger.info(msg)
                        local_lines.append(msg)
                        local_results.append({
                            "exchange": ex_id,
                            "path": path_str,
                            "net_pct": round(net_pct_adj if args.bf_revalidate_depth else net_pct, 4),
                            "inv": inv_amt,
                            "est_after": est_after,
                            "hops": hops,
                            "iteration": it,
                            "ts": ts,
                            **({
                                "net_pct_raw": round(net_pct, 4),
                                "slippage_bps": round(slip_bps, 2),
                                "fee_bps_total": round(fee_bps_total, 2),
                                "used_ws": used_ws_flag,
                            } if args.bf_revalidate_depth else {}),
                        })
                        cycles_found += 1
                        if cycles_found >= args.bf_top:
                            break
                if args.bf_debug:
                    logger.info("[BF-DBG] %s cycles_found=%d (min_net=%.3f%%)", ex_id, cycles_found, args.bf_min_net)
                time.sleep(args.sleep)
            except Exception as e:
                logger.warning("%s: BF scan fall├│: %s", ex_id, e)
            return ex_id, local_lines, local_results

        def tri_worker(ex_id: str, it: int, ts: str) -> Tuple[str, List[str], List[dict]]:
            """Per-exchange triangular worker (optimized).
            Collects results in-memory and returns them; caller performs IO/aggregation.
            """
            local_lines: List[str] = []
            local_results: List[dict] = []
            try:
                ex = load_exchange(ex_id, args.timeout)
                if not safe_has(ex, "fetchTickers"):
                    return ex_id, local_lines, local_results

                markets = ex.load_markets()
                tickers = ex.fetch_tickers()

                ex_norm = normalize_ccxt_id(ex_id)
                exchange_blacklist = swaps_blacklist_map.get(ex_norm, set())

                # Bind frequently used attrs to locals for speed
                tri_min_quote_vol = float(args.tri_min_quote_vol)
                tri_require_top = bool(args.tri_require_topofbook)
                tri_fee = float(args.tri_fee)
                tri_min_net = float(args.tri_min_net)
                tri_limit = int(args.tri_currencies_limit)
                tri_latency_penalty = float(getattr(args, "tri_latency_penalty_bps", 0.0))
                _pair_is_blacklisted_local = _pair_is_blacklisted
                get_rate_and_qvol_local = get_rate_and_qvol

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
                        if exchange_blacklist and _pair_is_blacklisted_local(exchange_blacklist, QUOTE, other_up):
                            continue
                        seen_tokens.add(other_up)
                        tokens_list.append(other_up)
                tokens = tokens_list[:tri_limit]
                if not tokens:
                    return ex_id, local_lines, local_results

                # Precompute r1_map and r3_map
                r1_map: Dict[str, tuple] = {}
                r3_map: Dict[str, tuple] = {}
                fee = tri_fee
                for tkn in tokens:
                    r1_map[tkn] = get_rate_and_qvol_local(QUOTE, tkn, tickers, fee, tri_require_top)
                    r3_map[tkn] = get_rate_and_qvol_local(tkn, QUOTE, tickers, fee, tri_require_top)

                from itertools import permutations
                from datetime import datetime

                ts_now = datetime.utcnow().isoformat()
                fee_bps_total = 3.0 * fee

                for X, Y in permutations(tokens, 2):
                    if exchange_blacklist and _pair_is_blacklisted_local(exchange_blacklist, X, Y):
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

        for it in range(1, int(max(1, args.repeat)) + 1):
            ts = pd.Timestamp.utcnow().isoformat()
            swaps_blacklist_map = load_swaps_blacklist()
            if do_console_clear:
                try:
                    if os.name == "nt":
                        os.system("cls")
                    else:
                        print("\033[2J\033[H", end="")
                except Exception:
                    pass
            # Clean per-iteration artifacts and any historical files to avoid mixing iterations
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
            # Create snapshot file immediately so users can follow progress from the beginning
            try:
                with open(current_file, "w", encoding="utf-8") as fh:
                    fh.write(f"[BF] Iteración {it}/{args.repeat} @ {ts}\n\n")
                    # Always show Simulation (estado actual) right after header (guarded by UI flag)
                    if getattr(args, "ui_show_simulation_header_always", True):
                        fh.write("Simulación (estado actual)\n")
                        try:
                            rows_sim_hdr = _build_simulation_rows(sim_state, args, wallet_buckets_cache)
                            if rows_sim_hdr:
                                df_sim_hdr = pd.DataFrame(rows_sim_hdr)
                            else:
                                df_sim_hdr = pd.DataFrame(columns=["exchange","currency","start_balance","balance","profit","roi_pct"])
                            fh.write(tabulate(df_sim_hdr, headers="keys", tablefmt="github", showindex=False))
                        except Exception:
                            fh.write("(sin datos)\n")
                        fh.write("\n")
                    # Progress header + initial bar (optional)
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
                    # Draw placeholder tables so structure is visible from the start (optional)
                    try:
                        if getattr(args, "ui_draw_tables_first", True):
                            # TOP oportunidades (vac├¡o)
                            df_top = pd.DataFrame(columns=["exchange","path","hops","net_pct","inv","est_after","ts"])
                            fh.write("TOP oportunidades (iteraci├│n)\n")
                            fh.write(tabulate(df_top, headers="keys", tablefmt="github", showindex=False))
                            fh.write("\n\n")
                    except Exception:
                        pass
                    try:
                        if getattr(args, "ui_draw_tables_first", True):
                            # Resumen por exchange (vac├¡o)
                            df_ex = pd.DataFrame(columns=["exchange","count","best_net"])
                            fh.write("Resumen por exchange (iteraci├│n)\n")
                            fh.write(tabulate(df_ex, headers="keys", tablefmt="github", showindex=False))
                            fh.write("\n\n")
                    except Exception:
                        pass
                    try:
                        if getattr(args, "ui_draw_tables_first", True):
                            # Simulaci├│n (estado actual) si aplica, con balances iniciales
                            if args.simulate_compound and sim_state:
                                rows_sim = []
                                for ex_id, st in sim_state.items():
                                    try:
                                        start_bal = float(st.get("start_balance", 0.0) or 0.0)
                                    except Exception:
                                        start_bal = 0.0
                                    bal = float(st.get("balance", 0.0) or 0.0)
                                    ccy = str(st.get("ccy", ""))
                                    # Display fallback: if using wallet and start_balance is 0 but balance>0, assume start equals current for reporting
                                    sb_disp = start_bal
                                    if getattr(args, "simulate_from_wallet", False) and sb_disp == 0.0 and bal > 0.0:
                                        sb_disp = bal
                                    roi = ((bal - sb_disp) / sb_disp * 100.0) if sb_disp > 0 else 0.0
                                    rows_sim.append({
                                        "exchange": ex_id,
                                        "currency": ccy,
                                        "start_balance": round(sb_disp, 8),
                                        "balance": round(bal, 8),
                                        "profit": round(bal - sb_disp, 8),
                                        "roi_pct": round(roi, 6),
                                    })
                                df_sim = pd.DataFrame(rows_sim)
                                fh.write("Simulaci├│n (estado actual)\n")
                                fh.write(tabulate(df_sim, headers="keys", tablefmt="github", showindex=False))
                                fh.write("\n\n")
                    except Exception:
                        pass
                    try:
                        if getattr(args, "ui_draw_tables_first", True):
                            # Persistencia (vac├¡o)
                            dfp = pd.DataFrame(columns=["exchange","path","occurrences","current_streak","max_streak","last_seen"])
                            fh.write("Persistencia (top)\n")
                            fh.write(tabulate(dfp, headers="keys", tablefmt="github", showindex=False))
                            fh.write("\n\n")
                    except Exception:
                        pass
                    fh.write("Detalle (progreso)\n")
                    fh.flush()
            except Exception:
                pass
            iter_lines: List[str] = []
            iter_results: List[dict] = []
            progress_started = True  # header ya impreso arriba
            completed_count = 0
            # Run workers (threaded or sequential)
            # If --bf_threads <= 0, use one thread per exchange. Otherwise, limit to the number of exchanges.
            configured_threads = int(args.bf_threads)
            num_workers = len(EX_IDS) if configured_threads <= 0 else min(configured_threads, len(EX_IDS))
            if max(1, num_workers) > 1:
                with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, num_workers)) as pool:
                    futures = [pool.submit(bf_worker, ex_id, it, ts) for ex_id in EX_IDS]
                    # also schedule tri workers so per-exchange triangular checks run in parallel with BF
                    tri_futures = [pool.submit(tri_worker, ex_id, it, ts) for ex_id in EX_IDS]
                    # Optional per-iteration timeout
                    deadline = None
                    try:
                        tsec = float(getattr(args, "bf_iter_timeout_sec", 0.0) or 0.0)
                        if tsec > 0:
                            deadline = time.time() + tsec
                    except Exception:
                        deadline = None
                    pending = set(futures) | set(tri_futures)
                    while pending:
                        timeout_next = None
                        if deadline is not None:
                            timeout_next = max(0.0, deadline - time.time())
                            if timeout_next == 0:
                                break
                        done, pending = concurrent.futures.wait(pending, timeout=timeout_next, return_when=concurrent.futures.FIRST_COMPLETED)
                        if not done:
                            continue
                        for fut in done:
                            try:
                                ex_id, lines, rows = fut.result()
                            except Exception as e:
                                ex_id, lines, rows = ("?", [f"worker error: {e}"], [])
                            iter_lines.extend(lines)
                            # Append progress lines and update progress bar as each worker completes
                            try:
                                with open(current_file, "a", encoding="utf-8") as fh:
                                        if getattr(args, "ui_progress_bar", True):
                                            completed_count += 1
                                            total_ex = max(1, len(EX_IDS))
                                            frames = str(getattr(args, "ui_spinner_frames", "|/-\\"))
                                            bar_len = int(getattr(args, "ui_progress_len", 20))
                                            filled = int(bar_len * completed_count / total_ex)
                                            bar = "[" + ("#" * filled) + ("-" * (bar_len - filled)) + "]"
                                            try:
                                                spinner = frames[completed_count % len(frames)] if frames else ""
                                            except Exception:
                                                spinner = ""
                                            fh.write(f"{bar} {completed_count}/{total_ex} {spinner}\n")
                                        if lines:
                                            fh.write("\n".join(lines) + "\n")
                                        # Append refreshed tables (partial view)
                                        try:
                                            # TOP oportunidades (parcial)
                                            try:
                                                top_k = []
                                                if iter_results:
                                                    top_k = sorted(iter_results, key=lambda r: float(r.get("net_pct", 0.0)), reverse=True)[:int(getattr(args, "bf_top", 3) or 3)]
                                                rows_top = []
                                                for r in top_k:
                                                    rows_top.append({
                                                        "exchange": r.get("exchange"),
                                                        "path": r.get("path"),
                                                        "hops": r.get("hops"),
                                                        "net_pct": round(float(r.get("net_pct", 0.0)), 3),
                                                        "inv": r.get("inv"),
                                                        "est_after": r.get("est_after"),
                                                        "ts": r.get("ts"),
                                                    })
                                                df_top = pd.DataFrame(rows_top if rows_top else [], columns=["exchange","path","hops","net_pct","inv","est_after","ts"])
                                                fh.write("\nTOP oportunidades (iteraci├│n)\n")
                                                fh.write(tabulate(df_top, headers="keys", tablefmt="github", showindex=False))
                                                fh.write("\n\n")
                                            except Exception:
                                                pass
                                            # Resumen por exchange (parcial)
                                            try:
                                                if iter_results:
                                                    agg = {}
                                                    for r in iter_results:
                                                        exr = r.get("exchange")
                                                        if not exr:
                                                            continue
                                                        net = float(r.get("net_pct", 0.0))
                                                        a = agg.setdefault(exr, {"count": 0, "best_net": -1e9})
                                                        a["count"] += 1
                                                        if net > a["best_net"]:
                                                            a["best_net"] = net
                                                    rows_ex = [{"exchange": ex, "count": v["count"], "best_net": round(v["best_net"], 3) if v["best_net"] > -1e9 else None} for ex, v in agg.items()]
                                                else:
                                                    rows_ex = []
                                                df_ex = pd.DataFrame(rows_ex if rows_ex else [], columns=["exchange","count","best_net"])
                                                fh.write("Resumen por exchange (iteraci├│n)\n")
                                                fh.write(tabulate(df_ex, headers="keys", tablefmt="github", showindex=False))
                                                fh.write("\n\n")
                                            except Exception:
                                                pass
                                            # Simulaci├│n (estado actual) (parcial)
                                            try:
                                                if args.simulate_compound and sim_state:
                                                    rows_sim = []
                                                    for ex_id2, st2 in sim_state.items():
                                                        try:
                                                            sb = float(st2.get("start_balance", 0.0) or 0.0)
                                                        except Exception:
                                                            sb = 0.0
                                                        bal2 = float(st2.get("balance", 0.0) or 0.0)
                                                        ccy2 = str(st2.get("ccy", ""))
                                                        roi2 = ((bal2 - sb) / sb * 100.0) if sb > 0 else 0.0
                                                        rows_sim.append({
                                                            "exchange": ex_id2,
                                                            "currency": ccy2,
                                                            "start_balance": round(sb, 8),
                                                            "balance": round(bal2, 8),
                                                            "profit": round(bal2 - sb, 8),
                                                            "roi_pct": round(roi2, 6),
                                                        })
                                                    df_sim2 = pd.DataFrame(rows_sim)
                                                    fh.write("Simulaci├│n (estado actual)\n")
                                                    fh.write(tabulate(df_sim2, headers="keys", tablefmt="github", showindex=False))
                                                    fh.write("\n\n")
                                            except Exception:
                                                pass
                                            # Persistencia (top) (parcial)
                                            try:
                                                if persistence:
                                                    prow = []
                                                    for (pex, ppath), pst in persistence.items():
                                                        prow.append({
                                                            "exchange": pex,
                                                            "path": ppath,
                                                            "occurrences": int(pst.get("occurrences", 0) or 0),
                                                            "current_streak": int(pst.get("current_streak", 0) or 0),
                                                            "max_streak": int(pst.get("max_streak", 0) or 0),
                                                            "last_seen": pst.get("last_seen"),
                                                        })
                                                    prow = sorted(prow, key=lambda r: (r["max_streak"], r["occurrences"]), reverse=True)[:10]
                                                    dfp2 = pd.DataFrame(prow, columns=["exchange","path","occurrences","current_streak","max_streak","last_seen"]) if prow else pd.DataFrame(columns=["exchange","path","occurrences","current_streak","max_streak","last_seen"])
                                                    fh.write("Persistencia (top)\n")
                                                    fh.write(tabulate(dfp2, headers="keys", tablefmt="github", showindex=False))
                                                    fh.write("\n\n")
                                            except Exception:
                                                pass
                                        except Exception:
                                            pass
                                        fh.flush()
                            except Exception:
                                pass
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
                    # If timed out, notify remaining
                    if pending:
                        try:
                            with open(current_file, "a", encoding="utf-8") as fh:
                                fh.write(f"\n[WARN] Iteraci├│n BF super├│ timeout de {getattr(args, 'bf_iter_timeout_sec', 0.0)}s; {len(pending)} exchanges sin completar.\n")
                                fh.flush()
                        except Exception:
                            pass
            else:
                for ex_id in EX_IDS:
                    _ex_id, lines, rows = bf_worker(ex_id, it, ts)
                    iter_lines.extend(lines)
                    # Update iteration results and persistence BEFORE rendering partial tables (avoid lagging display)
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
                    # Append progress lines in sequential mode as well, updating progress bar
                    try:
                        with open(current_file, "a", encoding="utf-8") as fh:
                            if getattr(args, "ui_progress_bar", True):
                                completed_count += 1
                                total_ex = max(1, len(EX_IDS))
                                frames = str(getattr(args, "ui_spinner_frames", "|/-\\"))
                                bar_len = int(getattr(args, "ui_progress_len", 20))
                                filled = int(bar_len * completed_count / total_ex)
                                bar = "[" + ("#" * filled) + ("-" * (bar_len - filled)) + "]"
                                try:
                                    spinner = frames[completed_count % len(frames)] if frames else ""
                                except Exception:
                                    spinner = ""
                                fh.write(f"{bar} {completed_count}/{total_ex} {spinner}\n")
                            if lines:
                                fh.write("\n".join(lines) + "\n")
                            # Append refreshed tables (partial view)
                            try:
                                # TOP oportunidades (parcial)
                                try:
                                    top_k = []
                                    if iter_results:
                                        top_k = sorted(iter_results, key=lambda r: float(r.get("net_pct", 0.0)), reverse=True)[:int(getattr(args, "bf_top", 3) or 3)]
                                    rows_top = []
                                    for r in top_k:
                                        rows_top.append({
                                            "exchange": r.get("exchange"),
                                            "path": r.get("path"),
                                            "hops": r.get("hops"),
                                            "net_pct": round(float(r.get("net_pct", 0.0)), 3),
                                            "inv": r.get("inv"),
                                            "est_after": r.get("est_after"),
                                            "ts": r.get("ts"),
                                        })
                                    df_top = pd.DataFrame(rows_top if rows_top else [], columns=["exchange","path","hops","net_pct","inv","est_after","ts"])
                                    fh.write("\nTOP oportunidades (iteraci├│n)\n")
                                    fh.write(tabulate(df_top, headers="keys", tablefmt="github", showindex=False))
                                    fh.write("\n\n")
                                except Exception:
                                    pass
                                # Resumen por exchange (parcial)
                                try:
                                    if iter_results:
                                        agg = {}
                                        for r in iter_results:
                                            exr = r.get("exchange")
                                            if not exr:
                                                continue
                                            net = float(r.get("net_pct", 0.0))
                                            a = agg.setdefault(exr, {"count": 0, "best_net": -1e9})
                                            a["count"] += 1
                                            if net > a["best_net"]:
                                                a["best_net"] = net
                                        rows_ex = [{"exchange": ex, "count": v["count"], "best_net": round(v["best_net"], 3) if v["best_net"] > -1e9 else None} for ex, v in agg.items()]
                                    else:
                                        rows_ex = []
                                    df_ex = pd.DataFrame(rows_ex if rows_ex else [], columns=["exchange","count","best_net"])
                                    fh.write("Resumen por exchange (iteraci├│n)\n")
                                    fh.write(tabulate(df_ex, headers="keys", tablefmt="github", showindex=False))
                                    fh.write("\n\n")
                                except Exception:
                                    pass
                                # Simulaci├│n (estado actual) (parcial)
                                try:
                                    if args.simulate_compound and sim_state:
                                        rows_sim = []
                                        for ex_id2, st2 in sim_state.items():
                                            try:
                                                sb = float(st2.get("start_balance", 0.0) or 0.0)
                                            except Exception:
                                                sb = 0.0
                                            bal2 = float(st2.get("balance", 0.0) or 0.0)
                                            ccy2 = str(st2.get("ccy", ""))
                                            # Display fallback when using wallet-based start and start is zero
                                            sb_disp = sb
                                            if getattr(args, "simulate_from_wallet", False) and sb_disp == 0.0 and bal2 > 0.0:
                                                sb_disp = bal2
                                            roi2 = ((bal2 - sb_disp) / sb_disp * 100.0) if sb_disp > 0 else 0.0
                                            rows_sim.append({
                                                "exchange": ex_id2,
                                                "currency": ccy2,
                                                "start_balance": round(sb_disp, 8),
                                                "balance": round(bal2, 8),
                                                "profit": round(bal2 - sb_disp, 8),
                                                "roi_pct": round(roi2, 6),
                                            })
                                        df_sim2 = pd.DataFrame(rows_sim)
                                        fh.write("Simulaci├│n (estado actual)\n")
                                        fh.write(tabulate(df_sim2, headers="keys", tablefmt="github", showindex=False))
                                        fh.write("\n\n")
                                except Exception:
                                    pass
                                # Persistencia (top) (parcial)
                                try:
                                    if persistence:
                                        prow = []
                                        for (pex, ppath), pst in persistence.items():
                                            prow.append({
                                                "exchange": pex,
                                                "path": ppath,
                                                "occurrences": int(pst.get("occurrences", 0) or 0),
                                                "current_streak": int(pst.get("current_streak", 0) or 0),
                                                "max_streak": int(pst.get("max_streak", 0) or 0),
                                                "last_seen": pst.get("last_seen"),
                                            })
                                        prow = sorted(prow, key=lambda r: (r["max_streak"], r["occurrences"]), reverse=True)[:10]
                                        dfp2 = pd.DataFrame(prow, columns=["exchange","path","occurrences","current_streak","max_streak","last_seen"]) if prow else pd.DataFrame(columns=["exchange","path","occurrences","current_streak","max_streak","last_seen"])
                                        fh.write("Persistencia (top)\n")
                                        fh.write(tabulate(dfp2, headers="keys", tablefmt="github", showindex=False))
                                        fh.write("\n\n")
                                except Exception:
                                    pass
                            except Exception:
                                pass
                            fh.flush()
                    except Exception:
                        pass


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
                            df_top = df_top.sort_values("net_pct", ascending=False).head(max(1, int(args.bf_top)))
                            # Overwrite file every iteration (no historical accumulation)
                            df_top.to_csv(bf_top_hist_csv, index=False)
                    except Exception:
                        pass
                # Overwrite the current-iteration CSV with this iteration's results
                try:
                    if iter_results:
                        pd.DataFrame(iter_results).to_csv(bf_iter_csv, index=False)
                    else:
                        pd.DataFrame(columns=["exchange","path","net_pct","inv","est_after","hops","iteration","ts"]).to_csv(bf_iter_csv, index=False)
                except Exception:
                    pass
                # Snapshot file: append final aggregated sections (keep earlier progress)
                with open(current_file, "a", encoding="utf-8") as fh:
                    fh.write("\n---\nResumen final (iteraci├│n)\n\n")
                    # 1) Top oportunidades de la iteraci├│n
                    try:
                        if iter_results:
                            df_iter = pd.DataFrame(iter_results)
                            df_top = df_iter.sort_values("net_pct", ascending=False).head(max(1, int(args.bf_top)))
                            cols_top = [c for c in ["exchange","path","hops","net_pct","inv","est_after","ts"] if c in df_top.columns]
                            fh.write("TOP oportunidades (iteraci├│n)\n")
                            fh.write(tabulate(df_top[cols_top], headers="keys", tablefmt="github", showindex=False))
                            fh.write("\n\n")
                        else:
                            fh.write("TOP oportunidades (iteraci├│n): (sin resultados)\n\n")
                    except Exception:
                        fh.write("TOP oportunidades (iteraci├│n): (error al generar tabla)\n\n")
                    # 2) Resumen por exchange de la iteraci├│n
                    try:
                        if iter_results:
                            df_iter = pd.DataFrame(iter_results)
                            grp = df_iter.groupby("exchange", as_index=False).agg(
                                count=("net_pct","count"),
                                best_net=("net_pct","max")
                            )
                            grp = grp.sort_values(["best_net","count"], ascending=[False, False])
                            fh.write("Resumen por exchange (iteraci├│n)\n")
                            fh.write(tabulate(grp, headers="keys", tablefmt="github", showindex=False))
                            fh.write("\n\n")
                    except Exception:
                        pass
                    # 3) Resumen de simulaci├│n (estado actual)
                    try:
                        if args.simulate_compound and sim_state:
                            rows_sim = []
                            for ex_id, st in sim_state.items():
                                try:
                                    start_bal = float(st.get("start_balance", st.get("balance", 0.0)) or 0.0)
                                except Exception:
                                    start_bal = 0.0
                                bal = float(st.get("balance", 0.0) or 0.0)
                                ccy = str(st.get("ccy", ""))
                                # Display-only: keep start_balance stable; do not fallback to current balance
                                # Avoid NaN in table when start_balance == 0
                                roi = ((bal - start_bal) / start_bal * 100.0) if start_bal > 0 else 0.0
                                rows_sim.append({
                                    "exchange": ex_id,
                                    "currency": ccy,
                                    "start_balance": round(start_bal, 8),
                                    "balance": round(bal, 8),
                                    "profit": round(bal - start_bal, 8),
                                    "roi_pct": round(roi, 6),
                                })
                            if rows_sim:
                                df_sim = pd.DataFrame(rows_sim)
                                fh.write("Simulaci├│n (estado actual)\n")
                                fh.write(tabulate(df_sim, headers="keys", tablefmt="github", showindex=False))
                                fh.write("\n\n")
                    except Exception:
                        pass
                    # 4) Persistencia (top por racha)
                    try:
                        if persistence:
                            prow = []
                            for (ex_id, path_str), st in persistence.items():
                                prow.append({
                                    "exchange": ex_id,
                                    "path": path_str,
                                    "occurrences": int(st.get("occurrences", 0)),
                                    "current_streak": int(st.get("current_streak", 0)),
                                    "max_streak": int(st.get("max_streak", 0)),
                                    "last_seen": st.get("last_seen"),
                                })
                            if prow:
                                dfp = pd.DataFrame(prow)
                                dfp = dfp.sort_values(["max_streak","occurrences"], ascending=[False, False]).head(10)
                                cols_p = [c for c in ["exchange","path","occurrences","current_streak","max_streak","last_seen"] if c in dfp.columns]
                                fh.write("Persistencia (top)\n")
                                fh.write(tabulate(dfp[cols_p], headers="keys", tablefmt="github", showindex=False))
                                fh.write("\n\n")
                    except Exception:
                        pass
                    # 5) Detalle texto final (incluye [SIM] picks por iteraci├│n)
                    # Ya se fueron agregando l├¡neas de progreso; a├▒adimos el detalle completo al final por conveniencia
                    if iter_lines:
                        fh.write("Detalle (iteraci├│n, completo)\n")
                        fh.write("\n".join(iter_lines) + "\n")
                    else:
                        fh.write("(sin oportunidades en esta iteraci├│n)\n")
                # No alias snapshot write (CURRENT_BF.txt is the canonical snapshot)
                # History file: append all iterations to keep a running log
                bf_hist = paths.LOGS_DIR / "bf_history.txt"
                with open(bf_hist, "a", encoding="utf-8") as fh:
                    fh.write(f"[BF] Iteraci├│n {it}/{args.repeat} @ {ts}\n")
                    if iter_lines:
                        fh.write("\n".join(iter_lines) + "\n\n")
                    else:
                        fh.write("(sin oportunidades en esta iteraci├│n)\n\n")
                # No alias writes for history to avoid duplicates and mixed-case filenames
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
                    roi_pct = ( (end_bal - start_bal) / start_bal * 100.0 ) if start_bal > 0 else 0.0
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
                    roi_txt = f"{(r['roi_pct'] if r['roi_pct'] is not None else 0.0):.4f}%"
                    logger.info("BF SIM SUM @%s: %s %.4f -> %s %.4f (ROI %s, it=%d)",
                                r["exchange"], r["start_currency"], r["start_balance"],
                                r["end_currency"], r["end_balance"], roi_txt, r["iterations"])
                logger.info("BF Simulation Summary CSV: %s", bf_sim_summary_csv)
            except Exception as e:
                logger.warning("No se pudo escribir el resumen de simulaci├│n BF: %s", e)
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
                    logger.warning("%s: omitido (no soporta fetchTicker p├║blico)", ex_id)
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
            logger.warning("%s: load_markets fall├│: %s", ex_id, e)

    bases_ordered = bases_ordered[: UNIVERSE_LIMIT]
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
                logger.warning("%s: fetch tickers fall├│: %s", ex_id, e)

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
            "Oportunidades: %d | Sin oportunidad: %d | Total s├¡mbolos: %d",
            0 if report.empty else len(report), len(no_opp_symbols), len(had_symbols),
        )
        lines: List[str] = []
        disclaimer = " [nota: datos multi-exchange; puede incluir venues no confiables o il├¡quidos]" if args.ex.strip().lower() == "all" else ""
        for _, r in report.head(args.top).iterrows():
            buy_p = fmt_price(float(r["buy_price"]))
            sell_p = fmt_price(float(r["sell_price"]))
            lines.append(
                f"{r['symbol']} => BUY@{r['buy_exchange']} {buy_p} ΓåÆ "
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
                fh.write(f"[INTER] Iteraci├│n {it}/{args.repeat} @ {now_ts}\n")
                if lines:
                    fh.write("\n".join(lines) + "\n")
                else:
                    fh.write("(sin oportunidades en esta iteraci├│n)\n")
            # History file (overwrite per iteration)
            inter_hist = paths.LOGS_DIR / "inter_history.txt"
            with open(inter_hist, "w", encoding="utf-8") as fh:
                fh.write(f"[INTER] Iteraci├│n {it}/{args.repeat} @ {now_ts}\n")
                if lines:
                    fh.write("\n".join(lines) + "\n\n")
                else:
                    fh.write("(sin oportunidades en esta iteraci├│n)\n\n")
        except Exception:
            pass
        if it < args.repeat:
            time.sleep(max(0.0, args.repeat_sleep))


if __name__ == "__main__":
    main()
