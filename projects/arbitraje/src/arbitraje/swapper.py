from __future__ import annotations

import logging
import os
import re
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import yaml

from . import paths
from .balance_fetcher import SpotBalanceFetcher
from .exchange_utils import load_exchange as _load_exchange
from .exchange_utils import normalize_ccxt_id as _normalize_ccxt_id

# Load .env from repo root and project root if python-dotenv is available
try:  # pragma: no cover
    from dotenv import load_dotenv  # type: ignore
    load_dotenv(dotenv_path=str(paths.MONOREPO_ROOT / ".env"), override=False)
    load_dotenv(dotenv_path=str(paths.PROJECT_ROOT / ".env"), override=False)
except Exception:  # pragma: no cover
    pass

logger = logging.getLogger("swapper")
logger.setLevel(logging.INFO)
logger.propagate = False
fmt = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
try:
    has_sh = any(isinstance(h, logging.StreamHandler) for h in logger.handlers)
except Exception:
    has_sh = False
if not has_sh:
    try:
        sh = logging.StreamHandler()
        sh.setFormatter(fmt)
        logger.addHandler(sh)
    except Exception:
        pass
try:
    paths.LOGS_DIR.mkdir(parents=True, exist_ok=True)
except Exception:
    pass
try:
    # Allow overriding the log file path via SWAPPER_LOG_FILE
    override = os.environ.get("SWAPPER_LOG_FILE")
    if override and override.strip():
        log_path_str = str(os.path.abspath(override.strip()))
    else:
        log_path_str = str((paths.LOGS_DIR / "swapper.log").resolve())
    has_fh = False
    for h in list(logger.handlers):
        try:
            if isinstance(h, logging.FileHandler) and getattr(h, "baseFilename", None):
                if str(h.baseFilename) == log_path_str:
                    has_fh = True
                    break
        except Exception:
            continue
    if not has_fh:
        fh = logging.FileHandler(log_path_str, encoding="utf-8")
        fh.setFormatter(fmt)
        logger.addHandler(fh)
except Exception:
    pass


@dataclass
class SwapHop:
    base: str
    quote: str

    @property
    def symbol(self) -> str:
        return f"{self.base}/{self.quote}"


@dataclass
class SwapPlan:
    exchange: str
    hops: List[SwapHop]
    amount: float
    raw_line: Optional[str] = None


@dataclass
class SwapResult:
    ok: bool
    status: str  # "positive" | "negative" | "failed" | "ok"
    amount_in: float
    amount_out: float
    delta: float
    details: Dict[str, object]
def _parse_bf_line(line: str) -> Optional[Tuple[str, List[str], int, str]]:
    try:
        m1 = re.search(r"BF@([a-zA-Z0-9_]+)\s+([A-Z0-9_\-]+(?:->[A-Z0-9_\-]+)+)\s+\((\d+)hops\)", line)
        if not m1:
            return None
        ex = m1.group(1)
        path_str = m1.group(2)
        hops = int(m1.group(3))
        nodes = path_str.split("->")
        m2 = re.search(r"\|\s*([A-Z]{3,6})\s+", line)
        anchor = m2.group(1) if m2 else nodes[0]
        return ex, nodes, hops, anchor
    except Exception:
        return None


class Swapper:
    """Isolated swap execution class (OOP).

    - Config-driven via YAML, independent from radar.
    - test mode: USDT<->USDC round-trip using top-of-book; amount=1.
    - real mode: execute provided hops on a single exchange via market/IOC.
    """

    def __init__(self, config_path: Optional[str] = None):
        self.config: Dict[str, object] = {}
        if config_path and os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as fh:
                self.config = yaml.safe_load(fh) or {}
        self.mode = str(self.config.get("mode", "test")).strip().lower()
        self.timeout_ms = int(self.config.get("timeout_ms", 15000))
        self.order_type = str(self.config.get("order_type", "market")).lower()
        self.time_in_force = str(self.config.get("time_in_force", "IOC")).upper()
        self.max_slippage_bps = float(self.config.get("max_slippage_bps", 25.0))
        self.min_notional = float(self.config.get("min_notional", 1.0))
        self.dry_run = bool(self.config.get("dry_run", False))
        # Optional: in round-trip paths (start_ccy == end_ccy), make the LAST hop a mirrored LIMIT
        # using the price and amount from the FIRST hop. This aims to "lock" the previously-detected
        # edge by only closing at the entry terms. If funds are insufficient, the last hop fails.
        self.roundtrip_mirror_last_leg = bool(self.config.get("roundtrip_mirror_last_leg", False))
        # Mirror tuning: how much better than the mirror price to require (bps), and
        # how much quantity/cost shortfall to tolerate due to fees (bps)
        self.roundtrip_mirror_price_offset_bps = float(self.config.get("roundtrip_mirror_price_offset_bps", 0.0))
        self.roundtrip_mirror_amount_tolerance_bps = float(
            self.config.get("roundtrip_mirror_amount_tolerance_bps", 0.0)
        )
        # Optional: TTL-based re-emit for last-hop mirror orders
        # After TTL seconds, if order is still open and mid moved favorably (toward entry),
        # cancel-and-replace at min(entry*(1-off), mid*(1-safety)) for buys; symmetric for sells.
        self.mirror_reemit_ttl_sec = int(self.config.get("mirror_reemit_ttl_sec", 0))
        self.mirror_reemit_safety_bps = float(self.config.get("mirror_reemit_safety_bps", 0.0))
        self.mirror_reemit_max = int(self.config.get("mirror_reemit_max", 0))
        # Optional: time-based relaxation to avoid being stuck at entry-bound when price runs away
        # After mirror_relax_after_sec, allow increasing (buy) or decreasing (sell) the protective bound
        # by relax_bps_per_ttl per TTL cycle, capped by mirror_relax_max_bps
        self.mirror_relax_after_sec = int(self.config.get("mirror_relax_after_sec", 0))
        self.mirror_relax_bps_per_ttl = float(self.config.get("mirror_relax_bps_per_ttl", 0.0))
        self.mirror_relax_max_bps = float(self.config.get("mirror_relax_max_bps", 0.0))
        # Optional: force-close the mirror after timeout (seconds); 0 disables
        self.mirror_close_timeout_sec = int(self.config.get("mirror_close_timeout_sec", 0))
        # Optional: guard to cap max loss vs entry (in bps) when force-closing; 0 disables guard
        self.roundtrip_allow_max_loss_bps = float(self.config.get("roundtrip_allow_max_loss_bps", 0.0))
        # Execution tuning (optional; defaults are fastest)
        self.settle_sleep_ms = int(self.config.get("settle_sleep_ms", 0))
        self.confirm_fill = bool(self.config.get("confirm_fill", False))
        # Sizing configuration (auto/fixed) with per-exchange/symbol overrides
        try:
            self.sizing_cfg: Dict[str, object] = dict(self.config.get("sizing") or {})
        except Exception:
            self.sizing_cfg = {}
        # Cached balance fetcher for live mode
        self._balance_fetcher = SpotBalanceFetcher(timeout_ms=self.timeout_ms)
        # Per-exchange minimums for test mode
        try:
            self.test_min_amounts: Dict[str, float] = {
                str(k).lower(): float(v)
                for k, v in (dict(self.config.get("test_min_amounts") or {}).items())
            }
        except Exception:
            self.test_min_amounts = {}

    def plan_from_bf_line(self, line: str, amount: Optional[float] = None) -> Optional[SwapPlan]:
        parsed = _parse_bf_line(line)
        if not parsed:
            return None
        ex, nodes, _hops, _anchor = parsed
        hops = [SwapHop(base=nodes[i], quote=nodes[i+1]) for i in range(len(nodes)-1)]
        if self.mode == "test":
            # Use per-exchange test minimum if available; fallback to 1.0
            amt = float(amount) if amount else float(self.test_min_amounts.get(_normalize_ccxt_id(ex), 1.0))
        else:
            amt = float(amount or 0.0)
        return SwapPlan(exchange=ex, hops=hops, amount=amt, raw_line=line)

    def run(self, plan: SwapPlan) -> SwapResult:
        if self.mode == "test":
            return self._run_test(plan)
        return self._run_real(plan)

    def _run_test(self, plan: SwapPlan) -> SwapResult:
        # Test mode: simulate the provided path using tickers, no orders, ignoring anchor entirely
        ex_id = plan.exchange
        amt_first = (
            plan.amount if plan.amount and plan.amount > 0
            else float(self.test_min_amounts.get(_normalize_ccxt_id(ex_id), 1.0))
        )
        try:
            ex = _load_exchange(ex_id, auth=False, timeout_ms=self.timeout_ms)
            if not plan.hops:
                return SwapResult(False, "failed", 0.0, 0.0, 0.0, {"reason": "no_hops"})
            # Start with base of first hop
            cur_ccy = plan.hops[0].base.upper()
            amount_cur = float(amt_first)
            fills: List[Dict[str, object]] = []
            amount_in_used = float(amount_cur)
            for hop in plan.hops:
                base, quote = hop.base.upper(), hop.quote.upper()
                sym1, sym2 = f"{base}/{quote}", f"{quote}/{base}"
                invert = False
                t = None
                try:
                    t = ex.fetch_ticker(sym1)
                    sym = sym1
                except Exception:
                    try:
                        t = ex.fetch_ticker(sym2)
                        sym = sym2
                        invert = True
                    except Exception:
                        return SwapResult(
                            False,
                            "failed",
                            amount_in_used,
                            amount_cur,
                            amount_cur - amount_in_used,
                            {"reason": "symbol_missing", "hop": f"{base}->{quote}"},
                        )
                price = None
                try:
                    if t is None:
                        t = ex.fetch_ticker(sym)
                    price = (t.get("bid") or t.get("ask") or t.get("last"))
                except Exception:
                    price = None
                if price is None or price == 0:
                    return SwapResult(
                        False,
                        "failed",
                        amount_in_used,
                        amount_cur,
                        amount_cur - amount_in_used,
                        {"reason": "no_price", "symbol": sym},
                    )
                if not invert:
                    # base/quote: sell base
                    amount_next = float(amount_cur) * float(price)
                else:
                    # quote/base: buy quote using base
                    amount_next = float(amount_cur) / float(price)
                fills.append({
                    "symbol": sym,
                    "side": ("sell" if not invert else "buy"),
                    "amount_in": amount_cur,
                    "amount_out": amount_next,
                    "price": float(price),
                    "simulated": True,
                })
                amount_cur = float(amount_next)
                cur_ccy = quote
            # If start and end currencies coincide, compute delta; else delta=0
            start_ccy = plan.hops[0].base.upper()
            end_ccy = plan.hops[-1].quote.upper()
            delta = (amount_cur - amount_in_used) if (start_ccy == end_ccy) else 0.0
            return SwapResult(
                True,
                "ok",
                amount_in_used,
                amount_cur,
                delta,
                {"exchange": ex_id, "fills": fills, "start_ccy": start_ccy, "final_ccy": cur_ccy},
            )
        except Exception as e:
            return SwapResult(False, "failed", amt_first, 0.0, -amt_first, {"error": str(e)})

    def _run_real(self, plan: SwapPlan) -> SwapResult:
        ex_id = plan.exchange
        ex = _load_exchange(ex_id, auth=True, timeout_ms=self.timeout_ms)
        # Warm markets to enable precision helpers and limits
        try:
            ex.load_markets()
        except Exception:
            pass
        # We will follow the path strictly: for each hop base->quote, use the actual free balance
        # of the source currency (base) as the amount to convert, ignoring the anchor for execution.
        # If plan.amount > 0, it caps only the first hop source amount.
        # If sizing.mode == auto and plan.amount == 0, compute automatic cap.
        def _get_override(ex_id_l: str, sym_l: str, key: str) -> Optional[float]:
            try:
                ovr = (self.sizing_cfg.get("overrides") or {})
                ex_map = (ovr or {}).get(ex_id_l.lower()) or {}
                # symbol overrides use uppercase key to match paths like ZEC/USDT
                v = (ex_map.get(sym_l.upper()) or {}).get(key)
                if v is None:
                    v = ex_map.get(key)
                return float(v) if v is not None else None
            except Exception:
                return None
        def _compute_auto_cap_usdt(ex_id_l: str, sym_l: str, start_ccy_l: str) -> Tuple[float, Dict[str, float]]:
            # Defaults
            mode = str((self.sizing_cfg.get("mode") or "")).lower()
            alpha = float(self.sizing_cfg.get("alpha_tob", 0.0) or 0.0)
            beta = float(self.sizing_cfg.get("beta_dv_pct", 0.0) or 0.0)
            min_usd = float(self.sizing_cfg.get("min_usd", 0.0) or 0.0)
            max_usd = float(self.sizing_cfg.get("max_usd", 0.0) or 0.0)
            ladder_n = int(self.sizing_cfg.get("ladder_levels", 1) or 1)
            ladder_step = float(self.sizing_cfg.get("ladder_step_bps", 0.0) or 0.0)
            # Apply overrides per exchange/symbol when present
            alpha = _get_override(ex_id_l, sym_l, "alpha_tob") or alpha
            beta = _get_override(ex_id_l, sym_l, "beta_dv_pct") or beta
            min_usd = _get_override(ex_id_l, sym_l, "min_usd") or min_usd
            max_usd = _get_override(ex_id_l, sym_l, "max_usd") or max_usd
            ladder_n = int(_get_override(ex_id_l, sym_l, "ladder_levels") or ladder_n)
            ladder_step = _get_override(ex_id_l, sym_l, "ladder_step_bps") or ladder_step
            # Derive top-of-book for start_ccy vs USDT if possible
            est_usd_price = 0.0
            try:
                # Prefer a direct USDT market, else try USDC
                syms = [f"{start_ccy_l}/USDT", f"USDT/{start_ccy_l}", f"{start_ccy_l}/USDC", f"USDC/{start_ccy_l}"]
                for s in syms:
                    try:
                        t = ex.fetch_ticker(s)
                        bid = float(t.get("bid") or 0.0)
                        ask = float(t.get("ask") or 0.0)
                        last = float(t.get("last") or 0.0)
                        mid = (bid + ask) / 2.0 if (bid > 0 and ask > 0) else (last if last > 0 else 0.0)
                        if mid and mid > 0:
                            if s.endswith("/USDT") or s.endswith("/USDC"):
                                est_usd_price = float(mid)
                            else:
                                est_usd_price = 1.0 / float(mid)
                            break
                    except Exception:
                        continue
            except Exception:
                est_usd_price = 0.0
            # Estimate daily vol percent from config or default; in this initial version, use beta directly if >0
            dv_pct = max(0.0, float(beta or 0.0))
            # Compute base target in USD using alpha over ToB; add beta factor if configured
            target_usd = 0.0
            if str(mode) == "auto":
                try:
                    # alpha is direct USD if <0 means disabled; assume alpha is USD size when est_usd_price > 0
                    target_usd = float(alpha or 0.0)
                    if dv_pct and dv_pct > 0.0 and est_usd_price > 0:
                        # lightweight: add proportional term dv_pct * $100 baseline
                        target_usd += 100.0 * dv_pct
                except Exception:
                    target_usd = 0.0
                # Clamp to min/max
                if min_usd and target_usd < min_usd:
                    target_usd = float(min_usd)
                if max_usd and max_usd > 0 and target_usd > max_usd:
                    target_usd = float(max_usd)
            meta = {
                "mode": 1.0 if str(mode) == "auto" else 0.0,
                "alpha_tob": float(alpha or 0.0),
                "beta_dv_pct": float(dv_pct or 0.0),
                "min_usd": float(min_usd or 0.0),
                "max_usd": float(max_usd or 0.0),
                "ladder_levels": float(ladder_n or 1),
                "ladder_step_bps": float(ladder_step or 0.0),
                "est_usd_price": float(est_usd_price or 0.0),
                "target_usd": float(target_usd or 0.0),
            }
            return float(target_usd), meta

        # Compute first hop cap in source currency units; base on plan.amount or auto sizing
        first_cap = float(plan.amount or 0.0)
        sizing_meta: Dict[str, float] = {}
        try:
            if (not first_cap or first_cap <= 0.0) and isinstance(self.sizing_cfg, dict):
                mode = str((self.sizing_cfg.get("mode") or "")).lower()
                if mode == "auto" and plan.hops:
                    start_ccy0 = plan.hops[0].base.upper()
                    # Use the second symbol in the path as proxy for symbol-level overrides
                    hop0 = plan.hops[0]
                    sym_guess = f"{hop0.base.upper()}/{hop0.quote.upper()}"
                    usd_cap, sizing_meta = _compute_auto_cap_usdt(ex_id, sym_guess, start_ccy0)
                    if usd_cap and usd_cap > 0:
                        # Convert USD cap to source units using ToB if available; else fallback to wallet later
                        est_price = float(sizing_meta.get("est_usd_price") or 0.0)
                        if est_price and est_price > 0:
                            first_cap = float(usd_cap) / float(est_price)
        except Exception:
            pass
        amount_cur = 0.0  # will be set after first order
        # Current currency is advanced per hop; initialize to first hop base for clarity
        cur_ccy = plan.hops[0].base.upper() if plan.hops else ""
        fills: List[Dict[str, object]] = []
        # Track how much was consumed on the first hop (for reporting and cap logic)
        amount_in_used: Optional[float] = None

        def _free_balance(currency: str) -> float:
            cur = currency.upper()
            # In dry-run prefer in-flight estimates to avoid unnecessary reads
            if self.dry_run and cur == cur_ccy:
                if float(amount_cur) > 0:
                    return float(amount_cur)
                try:
                    if (
                        amount_in_used is None
                        and cur == (plan.hops[0].base.upper() if plan.hops else cur)
                        and first_cap > 0
                    ):
                        return float(first_cap)
                except Exception:
                    pass
            try:
                return float(self._balance_fetcher.get_balance(ex_id, cur))
            except Exception:
                try:
                    b = ex.fetch_balance()
                    bucket = b.get("free") or b.get("total") or {}
                    return float((bucket or {}).get(cur, 0.0) or 0.0)
                except Exception:
                    return 0.0

        def _amount_to_precision(sym: str, amount: float) -> float:
            try:
                return float(ex.amount_to_precision(sym, amount))
            except Exception:
                return float(amount)

        def _currency_to_precision(currency: str, amount: float) -> float:
            # Used for cost-based buys (quote currency precision)
            try:
                return float(ex.currency_to_precision(currency, amount))
            except Exception:
                return float(amount)
        def _price_to_precision(sym: str, price: float) -> float:
            try:
                return float(ex.price_to_precision(sym, price))
            except Exception:
                return float(price)
        def _sum_fees(order_obj: dict) -> Dict[str, float]:
            fees_sum: Dict[str, float] = {}
            try:
                # Prefer unified 'fees'
                fees = order_obj.get("fees") or []
                if isinstance(fees, list):
                    for f in fees:
                        try:
                            cur = str(f.get("currency") or "").upper()
                            cost = float(f.get("cost") or 0.0)
                            if cur:
                                fees_sum[cur] = fees_sum.get(cur, 0.0) + cost
                        except Exception:
                            continue
                # Fallback to single 'fee'
                fee = order_obj.get("fee") or {}
                if isinstance(fee, dict):
                    cur = str(fee.get("currency") or "").upper()
                    cost = float(fee.get("cost") or 0.0)
                    if cur:
                        fees_sum[cur] = fees_sum.get(cur, 0.0) + cost
            except Exception:
                pass
            return fees_sum

        try:
            start_ccy = plan.hops[0].base.upper() if plan.hops else cur_ccy
            end_ccy = plan.hops[-1].quote.upper() if plan.hops else cur_ccy
            is_roundtrip = bool(plan.hops and (start_ccy == end_ccy))
            # Track FIRST hop executed price (quote per base) and out amount (new currency units)
            first_hop_unit_price_q_per_b: Optional[float] = None
            first_hop_out_amount: Optional[float] = None
            first_hop_base = plan.hops[0].base.upper() if plan.hops else ""
            first_hop_quote = plan.hops[0].quote.upper() if plan.hops else ""
            # Track the limit price used on the mirror order for observability
            mirror_limit_price_used: Optional[float] = None
            for idx, hop in enumerate(plan.hops):
                base, quote = hop.base.upper(), hop.quote.upper()
                sym1 = f"{base}/{quote}"
                sym2 = f"{quote}/{base}"
                invert = False
                # Determine symbol orientation using loaded markets (fast)
                try:
                    mkts = ex.markets or {}
                except Exception:
                    mkts = {}
                if sym1 in mkts:
                    sym = sym1
                elif sym2 in mkts:
                    sym = sym2
                    invert = True
                else:
                    # Neutralize amounts on failure to avoid unit mismatch confusion
                    ain = float(amount_in_used or 0.0)
                    return SwapResult(
                        False,
                        "failed",
                        ain,
                        ain,
                        0.0,
                        {"reason": "symbol_missing", "hop": f"{base}->{quote}", "cur_ccy": cur_ccy},
                    )

                # Trade strictly in the hop direction (base -> quote)
                sym_base, sym_quote = (base, quote) if not invert else (quote, base)
                # If symbol is base/quote, we sell base; if symbol is quote/base, we buy quote using base
                side = "sell" if not invert else "buy"

                # Determine source funds from real wallet balance of the hop's base currency
                src_free = _free_balance(base)
                src_to_use = float(src_free)
                if amount_in_used is None and first_cap > 0:
                    src_to_use = min(src_to_use, float(first_cap))
                # Log when there are no funds for the source but we are still attempting a hop
                try:
                    if src_free <= 0:
                        logger.info(
                            "no_funds | exchange=%s | hop=%d/%d | base=%s | quote=%s | attempted=true | note=zero-free-balance will fail",
                            ex_id,
                            int(idx + 1),
                            int(len(plan.hops or [])),
                            base,
                            quote,
                        )
                except Exception:
                    pass
                if src_to_use <= 0:
                    ain = float(amount_in_used or 0.0)
                    return SwapResult(
                        False,
                        "failed",
                        ain,
                        ain,
                        0.0,
                        {"reason": "no_funds_source", "source": base},
                    )

                params = {}
                # Default order params
                order_type = "market"

                try:
                    buy_uses_cost = getattr(ex, "id", "").lower() in ("bitget", "binance")
                except Exception:
                    buy_uses_cost = False

                # Only fetch ticker for dry-run simulations
                price = None
                if self.dry_run:
                    try:
                        t = ex.fetch_ticker(sym)
                        if side == "sell":
                            price = t.get("bid") or t.get("last")
                        else:
                            price = t.get("ask") or t.get("last")
                    except Exception:
                        price = None

                # Determine safe amount to send using only wallet balance and precision (no local min checks)
                try:
                    # Market metadata (kept if needed for precision helpers)
                    try:
                        market = (ex.markets or {}).get(sym) or {}
                    except Exception:
                        market = {}
                    if side == "buy":
                        if buy_uses_cost and not self.dry_run:
                            # Use quoteOrderQty equal to available base funds; let exchange enforce limits
                            cost = float(src_to_use)
                            params["quoteOrderQty"] = _currency_to_precision(sym_quote, cost)
                            amount_param = None  # do not derive base amount
                        else:
                            # Dry-run or exchanges without quoteOrderQty support: approximate using price
                            if price:
                                base_amt = float(src_to_use) / float(price)
                                amount_param = _amount_to_precision(sym, base_amt)
                            else:
                                amount_param = _amount_to_precision(sym, src_to_use)
                    else:
                        # Sell available base units from wallet
                        sell_amt = float(src_to_use)
                        amount_param = _amount_to_precision(sym, sell_amt)
                except Exception:
                    amount_param = float(src_to_use) if side == "sell" else None

                if self.dry_run:
                    fill_price = float(price or 0.0) if price else 0.0
                    if side == "sell":
                        # base -> quote
                        amount_next = float(amount_param) * float(price or 1.0)
                    else:
                        # quote -> base
                        amount_next = float(amount_param or 0.0)
                    # Prepare base fill record
                    fill_rec = {
                        "symbol": sym,
                        "side": side,
                        "amount_in": src_to_use,
                        "amount_out": amount_next,
                        "price": fill_price,
                        "simulated": True,
                    }
                    # If this is the last hop in a round-trip and mirror is enabled, also surface mirror observability
                    if (
                        self.roundtrip_mirror_last_leg
                        and bool(plan.hops)
                        and (plan.hops[0].base.upper() == plan.hops[-1].quote.upper())
                        and idx == (len(plan.hops) - 1)
                        and first_hop_unit_price_q_per_b
                        and first_hop_unit_price_q_per_b > 0
                        and first_hop_out_amount is not None
                    ):
                        try:
                            if not invert:
                                limit_price_sim = float(1.0 / float(first_hop_unit_price_q_per_b))
                            else:
                                limit_price_sim = float(first_hop_unit_price_q_per_b)
                            off = float(self.roundtrip_mirror_price_offset_bps or 0.0) / 10000.0
                            if off and off > 0:
                                if side == "buy":
                                    limit_price_sim = float(max(0.0, limit_price_sim * (1.0 - off)))
                                else:
                                    limit_price_sim = float(limit_price_sim * (1.0 + off))
                            fill_rec.update({
                                "mirror_last_leg": True,
                                "mirror_first_price_q_per_b": float(first_hop_unit_price_q_per_b or 0.0),
                                "mirror_price_offset_bps": float(self.roundtrip_mirror_price_offset_bps or 0.0),
                                "mirror_amount_tolerance_bps": float(self.roundtrip_mirror_amount_tolerance_bps or 0.0),
                                "mirror_limit_price": float(limit_price_sim or 0.0),
                                "last_symbol": sym,
                                "last_side": side,
                            })
                        except Exception:
                            pass
                    fills.append(fill_rec)
                    amount_cur = float(amount_next)
                    cur_ccy = quote
                    if amount_in_used is None:
                        amount_in_used = float(src_to_use)
                    # Capture first hop references for mirrored last-leg if requested
                    if idx == 0 and self.roundtrip_mirror_last_leg and is_roundtrip:
                        try:
                            # price here is in sym units (sym_quote per sym_base)
                            eff_avg = float(price or 0.0)
                            if eff_avg and eff_avg > 0:
                                # Normalize to (first_hop_quote per first_hop_base)
                                # If symbol was base/quote == first_hop_base/first_hop_quote (not invert), keep as-is
                                # Else invert the price
                                if (not invert and base == first_hop_base and quote == first_hop_quote) or (
                                    invert and base == first_hop_quote and quote == first_hop_base
                                ):
                                    # invert==True here implies sym is first_hop_quote/first_hop_base, so invert the price
                                    first_hop_unit_price_q_per_b = (1.0 / eff_avg) if invert else eff_avg
                                else:
                                    first_hop_unit_price_q_per_b = eff_avg if not invert else (1.0 / eff_avg)
                            first_hop_out_amount = float(amount_next)
                        except Exception:
                            pass
                    continue

                # Capture first-hop input now for accurate reporting
                if amount_in_used is None:
                    amount_in_used = float(src_to_use)

                order_amount = amount_param
                if side == "buy" and buy_uses_cost and "quoteOrderQty" in params:
                    order_amount = None  # let exchange compute base from quote cost
                # If this is the LAST hop in a round-trip and mirror is enabled, place a LIMIT "mirror" order
                if (
                    self.roundtrip_mirror_last_leg
                    and is_roundtrip
                    and idx == (len(plan.hops) - 1)
                    and first_hop_unit_price_q_per_b
                    and first_hop_unit_price_q_per_b > 0
                    and first_hop_out_amount is not None
                ):
                    try:
                        # Compute mirrored price in current symbol orientation
                        # sym price unit is sym_quote per sym_base
                        # Keep track of entry price in symbol units (without offset) for re-emit checks
                        entry_sym_price = None
                        if not invert:
                            # sym is base/quote i.e., (B/A) for final hop; need A per B => invert first price
                            entry_sym_price = float(1.0 / float(first_hop_unit_price_q_per_b))
                            limit_price = float(entry_sym_price)
                        else:
                            # sym is quote/base i.e., (A/B); need A per B which equals first price as-is
                            entry_sym_price = float(first_hop_unit_price_q_per_b)
                            limit_price = float(entry_sym_price)

                        # Apply price offset bps: for buys we want cheaper (minus), for sells we want better (plus)
                        try:
                            off = float(self.roundtrip_mirror_price_offset_bps or 0.0) / 10000.0
                            if off and off > 0:
                                if side == "buy":
                                    limit_price = float(max(0.0, limit_price * (1.0 - off)))
                                else:
                                    limit_price = float(limit_price * (1.0 + off))
                        except Exception:
                            pass

                        # Determine mirrored amount: aim to use exactly the first hop's out amount of the non-anchor
                        # Last hop base currency is the source of funds in this hop ("base")
                        tol = float(self.roundtrip_mirror_amount_tolerance_bps or 0.0) / 10000.0
                        # Fetch market limits/precision for validation
                        try:
                            market = (ex.markets or {}).get(sym) or {}
                        except Exception:
                            market = {}
                        def _get_min(d: dict, *keys) -> Optional[float]:
                            cur = d
                            try:
                                for k in keys:
                                    cur = cur.get(k) or {}
                                v = float(cur) if isinstance(cur, (int, float)) else None
                            except Exception:
                                v = None
                            return v
                        limits = market.get("limits") or {}
                        min_amount = None
                        min_cost = None
                        try:
                            min_amount = float(((limits.get("amount") or {}).get("min")) or 0) or None
                        except Exception:
                            min_amount = None
                        try:
                            # prefer cost.min; some exchanges use notional
                            min_cost = float(((limits.get("cost") or {}).get("min")) or 0) or None
                        except Exception:
                            min_cost = None
                        # Stash variables for potential re-emit
                        mirror_needed_amount_base = None  # type: Optional[float]
                        mirror_needed_cost_quote = None   # type: Optional[float]
                        if not invert:
                            # sym is base/quote == B/A and side == 'sell'; amount is in B units
                            needed_amount = float(first_hop_out_amount)
                            if src_to_use + 1e-12 < needed_amount:
                                # Allow small shortfall within tolerance by reducing to available free balance
                                if tol > 0 and src_to_use >= needed_amount * (1.0 - tol):
                                    needed_amount = float(src_to_use)
                                else:
                                    ain = float(amount_in_used or 0.0)
                                    return SwapResult(
                                        False,
                                        "failed",
                                        ain,
                                        ain,
                                        0.0,
                                        {"reason": "mirror_insufficient_funds", "needed": needed_amount, "free": src_to_use, "symbol": sym},
                                    )
                            # Enforce min amount if available
                            if min_amount is not None and needed_amount < float(min_amount):
                                # If wallet can cover the min amount, bump; else fail
                                if src_to_use >= float(min_amount):
                                    needed_amount = float(min_amount)
                                else:
                                    ain = float(amount_in_used or 0.0)
                                    return SwapResult(
                                        False,
                                        "failed",
                                        ain,
                                        ain,
                                        0.0,
                                        {"reason": "mirror_below_min_amount", "min_amount": float(min_amount), "free": src_to_use, "symbol": sym},
                                    )
                            mirror_needed_amount_base = float(needed_amount)
                            order_amount = _amount_to_precision(sym, needed_amount)
                        else:
                            # sym is quote/base == A/B and side == 'buy'; exchange expects base (A) amount
                            # Spend exactly first_hop_out_amount of B at price limit_price
                            needed_cost_b = float(first_hop_out_amount)
                            if src_to_use + 1e-12 < needed_cost_b:
                                # Allow small shortfall within tolerance by reducing cost to available
                                if tol > 0 and src_to_use >= needed_cost_b * (1.0 - tol):
                                    needed_cost_b = float(src_to_use)
                                else:
                                    ain = float(amount_in_used or 0.0)
                                    return SwapResult(
                                        False,
                                        "failed",
                                        ain,
                                        ain,
                                        0.0,
                                        {"reason": "mirror_insufficient_funds", "needed": needed_cost_b, "free": src_to_use, "symbol": sym},
                                    )
                            # Enforce min notional (cost) if available by bumping cost up to min_cost (bounded by wallet)
                            if min_cost is not None and needed_cost_b < float(min_cost):
                                if src_to_use >= float(min_cost):
                                    needed_cost_b = float(min_cost)
                                else:
                                    ain = float(amount_in_used or 0.0)
                                    return SwapResult(
                                        False,
                                        "failed",
                                        ain,
                                        ain,
                                        0.0,
                                        {"reason": "mirror_below_min_notional", "min_cost": float(min_cost), "free": src_to_use, "symbol": sym},
                                    )
                            qty_a = needed_cost_b / float(limit_price)
                            # Enforce min amount too if present
                            if min_amount is not None and qty_a < float(min_amount):
                                # Try to raise qty to min_amount if wallet can cover its cost
                                min_cost_needed = float(min_amount) * float(limit_price)
                                if src_to_use >= min_cost_needed:
                                    qty_a = float(min_amount)
                                else:
                                    ain = float(amount_in_used or 0.0)
                                    return SwapResult(
                                        False,
                                        "failed",
                                        ain,
                                        ain,
                                        0.0,
                                        {"reason": "mirror_below_min_amount", "min_amount": float(min_amount), "free": src_to_use, "symbol": sym},
                                    )
                            mirror_needed_cost_quote = float(needed_cost_b)
                            order_amount = _amount_to_precision(sym, qty_a)

                        order_type = "limit"
                        # TimeInForce for limit: default to configured value
                        tif = str(self.time_in_force or "GTC").upper()
                        params = dict(params)
                        params["timeInForce"] = tif
                        # Apply price precision to reduce rejections (tick size)
                        limit_price = _price_to_precision(sym, float(limit_price))
                        # Save for observability outside this block
                        mirror_limit_price_used = float(limit_price)
                        order = ex.create_order(
                            symbol=sym,
                            type=order_type,
                            side=side,
                            amount=order_amount,
                            price=float(limit_price),
                            params=params,
                        )
                        try:
                            logger.info(
                                "mirror_placed | symbol=%s | side=%s | limit=%.8f | amount=%.8f | entry=%.8f | tol_bps=%.2f | sizing_mode=%s | first_cap_units=%.8f",
                                sym,
                                side,
                                float(limit_price or 0.0),
                                float(order_amount or 0.0),
                                float(entry_sym_price or 0.0),
                                float(self.roundtrip_mirror_amount_tolerance_bps or 0.0),
                                ("auto" if sizing_meta.get("mode") else "manual"),
                                float(first_cap or 0.0),
                            )
                        except Exception:
                            pass
                    except Exception as e:
                        # If the exchange complains about insufficient position, retry once with a reduced amount
                        err_text = str(e)
                        retry_done = False
                        if any(s in err_text.lower() for s in ["insufficient", "not enough", "30004"]):
                            try:
                                red = max(tol, 0.002)  # at least 20 bps reduction
                                if not invert:
                                    # Reduce base amount for sell
                                    amt0 = float(order_amount or 0.0)
                                    amt2 = _amount_to_precision(sym, max(0.0, amt0 * (1.0 - red)))
                                    if amt2 and amt2 > 0:
                                        order = ex.create_order(
                                            symbol=sym,
                                            type=order_type,
                                            side=side,
                                            amount=amt2,
                                            price=float(limit_price),
                                            params=params,
                                        )
                                        retry_done = True
                                else:
                                    # Buy side: spend slightly less quote to cover fees/precision
                                    max_cost = float(src_to_use) * (1.0 - red)
                                    qty2 = max_cost / float(limit_price)
                                    # Honor min amount if present; if below, give up (cannot cover minimum)
                                    if (min_amount is not None) and (qty2 < float(min_amount)):
                                        retry_done = False
                                    else:
                                        amt2 = _amount_to_precision(sym, max(0.0, qty2))
                                        if amt2 and amt2 > 0:
                                            order = ex.create_order(
                                                symbol=sym,
                                                type=order_type,
                                                side=side,
                                                amount=amt2,
                                                price=float(limit_price),
                                                params=params,
                                            )
                                            retry_done = True
                            except Exception as e2:
                                retry_done = False
                                err_text = f"{err_text} | retry_failed: {str(e2)}"
                        if not retry_done:
                            ain = float(amount_in_used or 0.0)
                            return SwapResult(
                                False,
                                "failed",
                                ain,
                                ain,
                                0.0,
                                {"reason": "mirror_order_error", "error": err_text, "symbol": sym},
                            )
                else:
                    order = ex.create_order(
                        symbol=sym,
                        type=order_type,
                        side=side,
                        amount=order_amount,
                        price=None,
                        params=params,
                    )
                # Optional settling delay to allow balances to update (only if configured)
                if self.settle_sleep_ms > 0:
                    try:
                        time.sleep(self.settle_sleep_ms / 1000.0)
                    except Exception:
                        pass
                try:
                    oid = order.get("id") if isinstance(order, dict) else None
                except Exception:
                    oid = None
                filled_out = None
                order_fees: Dict[str, float] = _sum_fees(order if isinstance(order, dict) else {})
                if self.confirm_fill and oid:
                    try:
                        o2 = ex.fetch_order(oid, sym)
                        filled = float(o2.get("filled") or 0.0)
                        avg = float(o2.get("average") or o2.get("price") or (price or 0.0))
                        order_fees = _sum_fees(o2) or order_fees
                        if side == "sell":
                            gross = filled * avg
                            # Subtract fees charged in quote currency
                            fee_q = float(order_fees.get(sym_quote, 0.0) or 0.0)
                            filled_out = max(0.0, gross - fee_q)
                        else:
                            # Net base after fees charged in base currency
                            fee_b = float(order_fees.get(sym_base, 0.0) or 0.0)
                            filled_out = max(0.0, filled - fee_b)
                    except Exception:
                        filled_out = None
                if filled_out is None and isinstance(order, dict):
                    try:
                        filled = float(order.get("filled") or 0.0)
                        avg = float(order.get("average") or order.get("price") or (price or 0.0))
                        if filled and avg:
                            if side == "sell":
                                gross = filled * avg
                                fee_q = float(order_fees.get(sym_quote, 0.0) or 0.0)
                                filled_out = max(0.0, gross - fee_q)
                            else:
                                fee_b = float(order_fees.get(sym_base, 0.0) or 0.0)
                                filled_out = max(0.0, filled - fee_b)
                    except Exception:
                        pass

                # Advance along the hop path to the target currency
                cur_ccy = quote
                amount_cur = float(filled_out or 0.0)
                if not self.dry_run:
                    # Read actual free balance for the next hop (optional extra small wait only if configured)
                    if self.settle_sleep_ms > 0:
                        try:
                            time.sleep(self.settle_sleep_ms / 1000.0)
                        except Exception:
                            pass
                    try:
                        real_free = _free_balance(cur_ccy)
                        amount_cur = float(real_free)
                    except Exception:
                        pass

                # Record fill using the best available realized amount
                out_val = float(amount_cur)
                fills.append(
                    {
                        "symbol": sym,
                        "side": side,
                        "amount_in": src_to_use,
                        "amount_out": out_val,
                        "order_id": oid,
                        "fees": order_fees,
                        "sizing": {
                            **({"mode": ("auto" if sizing_meta.get("mode") else "manual")}),
                            **({k: float(v) for k, v in sizing_meta.items()} if sizing_meta else {}),
                            "first_cap_units": float(first_cap or 0.0),
                        },
                        "mirror_last_leg": bool(
                            self.roundtrip_mirror_last_leg and is_roundtrip and idx == (len(plan.hops) - 1)
                        ),
                        # Observability for mirror
                        **({
                            "mirror_first_price_q_per_b": float(first_hop_unit_price_q_per_b or 0.0),
                            "mirror_price_offset_bps": float(self.roundtrip_mirror_price_offset_bps or 0.0),
                            "mirror_amount_tolerance_bps": float(self.roundtrip_mirror_amount_tolerance_bps or 0.0),
                            "mirror_limit_price": float(mirror_limit_price_used or 0.0),
                            "last_symbol": sym,
                            "last_side": side,
                        } if (self.roundtrip_mirror_last_leg and is_roundtrip and idx == (len(plan.hops) - 1)) else {}),
                    }
                )

                # Optional TTL-based re-emit for mirror last leg (real mode only)
                if (
                    self.roundtrip_mirror_last_leg
                    and is_roundtrip
                    and idx == (len(plan.hops) - 1)
                    and not self.dry_run
                    and oid
                    and int(self.mirror_reemit_ttl_sec or 0) > 0
                    and int(self.mirror_reemit_max or 0) > 0
                ):
                    try:
                        # Establish protective bound (original mirror limit price) and safety adjustment
                        protective_bound = float(mirror_limit_price_used or 0.0)
                        safety = float(self.mirror_reemit_safety_bps or 0.0) / 10000.0
                        # Track original placement time to report elapsed seconds
                        orig_ts = time.time()
                        max_reemits = int(self.mirror_reemit_max)
                        for _i in range(max_reemits):
                            try:
                                time.sleep(max(0, int(self.mirror_reemit_ttl_sec)))
                            except Exception:
                                pass
                            # Compute elapsed seconds since original mirror placement
                            try:
                                elapsed_s = int(max(0.0, time.time() - orig_ts))
                            except Exception:
                                elapsed_s = 0
                            # Force-close path (optional)
                            try:
                                if int(self.mirror_close_timeout_sec or 0) > 0 and elapsed_s >= int(self.mirror_close_timeout_sec):
                                    # Attempt to cancel current order
                                    try:
                                        ex.cancel_order(oid, sym)
                                    except Exception:
                                        pass
                                    # Loss guard check vs entry
                                    loss_guard_ok = True
                                    try:
                                        allow_loss_bps = float(self.roundtrip_allow_max_loss_bps or 0.0)
                                        if allow_loss_bps > 0.0 and entry_sym_price:
                                            if side == "buy":
                                                limit = float(entry_sym_price) * (1.0 + allow_loss_bps / 10000.0)
                                                # Fetch mid to evaluate guard
                                                t0 = ex.fetch_ticker(sym)
                                                bid0 = float(t0.get("bid") or 0.0)
                                                ask0 = float(t0.get("ask") or 0.0)
                                                last0 = float(t0.get("last") or 0.0)
                                                mid0 = (bid0 + ask0) / 2.0 if (bid0 > 0 and ask0 > 0) else (last0 if last0 > 0 else 0.0)
                                                if mid0 and mid0 > limit:
                                                    loss_guard_ok = False
                                            else:
                                                limit = float(entry_sym_price) * (1.0 - allow_loss_bps / 10000.0)
                                                t0 = ex.fetch_ticker(sym)
                                                bid0 = float(t0.get("bid") or 0.0)
                                                ask0 = float(t0.get("ask") or 0.0)
                                                last0 = float(t0.get("last") or 0.0)
                                                mid0 = (bid0 + ask0) / 2.0 if (bid0 > 0 and ask0 > 0) else (last0 if last0 > 0 else 0.0)
                                                if mid0 and mid0 < limit:
                                                    loss_guard_ok = False
                                    except Exception:
                                        loss_guard_ok = True
                                    if not loss_guard_ok:
                                        try:
                                            logger.info(
                                                "mirror_forced_close_skipped | symbol=%s | side=%s | entry=%.8f | allow_loss_bps=%.2f | elapsed_s=%d",
                                                sym,
                                                side,
                                                float(entry_sym_price or 0.0),
                                                float(self.roundtrip_allow_max_loss_bps or 0.0),
                                                int(elapsed_s),
                                            )
                                        except Exception:
                                            pass
                                        break
                                    # Place market order to close remainder
                                    try:
                                        # Determine remaining amount/cost
                                        amt_mkt = order_amount
                                        if side == "buy":
                                            # compute qty from quote budget and current ask/last
                                            tt = ex.fetch_ticker(sym)
                                            _ask = float(tt.get("ask") or 0.0)
                                            _last = float(tt.get("last") or 0.0)
                                            px = _ask if _ask > 0 else _last
                                            if mirror_needed_cost_quote is not None and px > 0:
                                                qty_mkt = float(mirror_needed_cost_quote) / float(px)
                                                amt_mkt = _amount_to_precision(sym, qty_mkt)
                                        # Minimum checks
                                        if (min_amount is not None) and (float(amt_mkt) < float(min_amount)):
                                            break
                                        o_fc = ex.create_order(
                                            symbol=sym,
                                            type="market",
                                            side=side,
                                            amount=amt_mkt,
                                            params=params,
                                        )
                                        try:
                                            logger.info(
                                                "mirror_forced_close | symbol=%s | side=%s | market_amount=%.8f | entry=%.8f | elapsed_s=%d | old_oid=%s | new_oid=%s",
                                                sym,
                                                side,
                                                float(amt_mkt or 0.0),
                                                float(entry_sym_price or 0.0),
                                                int(elapsed_s),
                                                str(oid),
                                                str((o_fc.get("id") if isinstance(o_fc, dict) else "") or ""),
                                            )
                                        except Exception:
                                            pass
                                    except Exception:
                                        pass
                                    break
                            except Exception:
                                pass
                            # Check if still open
                            try:
                                o_cur = ex.fetch_order(oid, sym)
                                filled_cur = float(o_cur.get("filled") or 0.0)
                                status_cur = str(o_cur.get("status") or "").lower()
                                if filled_cur > 0 or status_cur in ("closed", "canceled"):
                                    break  # nothing to do
                            except Exception:
                                # If we can't fetch, best-effort proceed to ticker check
                                pass
                            # Fetch mid and see if it moved favorably vs entry
                            try:
                                t = ex.fetch_ticker(sym)
                                bid = float(t.get("bid") or 0.0)
                                ask = float(t.get("ask") or 0.0)
                                last = float(t.get("last") or 0.0)
                                mid = (bid + ask) / 2.0 if (bid > 0 and ask > 0) else (last if last > 0 else 0.0)
                            except Exception:
                                mid = 0.0
                            if not mid or not entry_sym_price:
                                continue
                            new_price = None
                            # Compute relaxation used (in bps) based on elapsed time and TTL cycles
                            relax_used_bps = 0.0
                            try:
                                if int(self.mirror_relax_after_sec or 0) > 0 and elapsed_s >= int(self.mirror_relax_after_sec):
                                    step_bps = float(self.mirror_relax_bps_per_ttl or 0.0)
                                    if step_bps > 0.0:
                                        steps = (_i + 1)
                                        relax_used_bps = min(float(self.mirror_relax_max_bps or 0.0), steps * step_bps)
                            except Exception:
                                relax_used_bps = 0.0
                            if side == "buy":
                                # Favorable only if mid < entry (strict mode)
                                if mid < float(entry_sym_price):
                                    cand = float(mid) * (1.0 - safety) if safety > 0 else float(mid)
                                    new_price = min(float(protective_bound), float(cand))
                                # Relaxed mode: allow crossing entry up to relax_used_bps ceiling
                                elif relax_used_bps > 0.0:
                                    try:
                                        allowed_ceiling = float(entry_sym_price) * (1.0 + relax_used_bps / 10000.0)
                                        # Place near current bid to maximize maker chances, but never exceed allowed ceiling
                                        target_level = bid if bid > 0 else mid
                                        new_price = min(float(allowed_ceiling), max(float(protective_bound), float(target_level)))
                                    except Exception:
                                        new_price = None
                            else:
                                # Sell: favorable only if mid > entry; push price up but never above protective bound
                                if mid > float(entry_sym_price):
                                    cand = float(mid) * (1.0 + safety) if safety > 0 else float(mid)
                                    new_price = max(float(protective_bound), float(cand))
                                # Relaxed mode: allow going below entry down to relax_used_bps floor
                                elif relax_used_bps > 0.0:
                                    try:
                                        allowed_floor = float(entry_sym_price) * (1.0 - relax_used_bps / 10000.0)
                                        # Place near current ask for maker chances, but not below allowed_floor
                                        target_level = ask if ask > 0 else mid
                                        new_price = max(float(allowed_floor), min(float(protective_bound), float(target_level)))
                                    except Exception:
                                        new_price = None
                            if new_price is None:
                                continue
                            # If change is negligible, skip
                            try:
                                if abs(float(new_price) - float(protective_bound)) <= (abs(protective_bound) * 1e-6 + 1e-10):
                                    continue
                            except Exception:
                                pass
                            # Apply price precision
                            new_price_prec = _price_to_precision(sym, float(new_price))
                            # Cancel and replace
                            try:
                                ex.cancel_order(oid, sym)
                            except Exception:
                                pass
                            # Recompute amount if needed (buy side uses price-dependent qty)
                            amt2 = order_amount
                            if side == "buy" and mirror_needed_cost_quote is not None:
                                qty2 = float(mirror_needed_cost_quote) / float(new_price_prec)
                                if (min_amount is not None) and (qty2 < float(min_amount)):
                                    # Can't meet minimum; skip re-emit
                                    continue
                                amt2 = _amount_to_precision(sym, qty2)
                            # Place new order
                            try:
                                o_new = ex.create_order(
                                    symbol=sym,
                                    type=order_type,
                                    side=side,
                                    amount=amt2,
                                    price=float(new_price_prec),
                                    params=params,
                                )
                                # Audit log: explicit record of re-emit (old_limit -> new_limit)
                                try:
                                    attempt_idx = _i + 1
                                    try:
                                        _old = float(protective_bound or 0.0)
                                        _new = float(new_price_prec or 0.0)
                                        delta_bps = (abs(_new - _old) / _old * 10000.0) if _old else 0.0
                                    except Exception:
                                        delta_bps = 0.0
                                    logger.info(
                                        "mirror_reemit | symbol=%s | side=%s | old_limit=%.8f | new_limit=%.8f | delta_bps=%.2f | relax_used_bps=%.2f | mid=%.8f | entry=%.8f | old_oid=%s | new_oid=%s | attempt=%d/%d | elapsed_s=%d",
                                        sym,
                                        side,
                                        float(protective_bound or 0.0),
                                        float(new_price_prec or 0.0),
                                        float(delta_bps),
                                        float(relax_used_bps),
                                        float(mid or 0.0),
                                        float(entry_sym_price or 0.0),
                                        str(oid),
                                        str((o_new.get("id") if isinstance(o_new, dict) else "") or ""),
                                        int(attempt_idx),
                                        int(max_reemits),
                                        int(elapsed_s),
                                    )
                                except Exception:
                                    pass
                                try:
                                    oid = o_new.get("id") or oid
                                except Exception:
                                    pass
                                protective_bound = float(new_price_prec)
                                mirror_limit_price_used = float(new_price_prec)
                            except Exception:
                                # Failed to re-emit; keep original
                                break
                    except Exception:
                        pass

                # If this was the first hop, capture reference price and amount for mirrored last-leg (real mode)
                if idx == 0 and self.roundtrip_mirror_last_leg and is_roundtrip:
                    try:
                        # Try to compute an effective average price from available info
                        eff_avg = 0.0
                        try:
                            if isinstance(order, dict):
                                eff_avg = float(order.get("average") or order.get("price") or 0.0)
                        except Exception:
                            eff_avg = 0.0
                        # Fallback: derive from realized amounts if no avg/price returned by exchange
                        if (not eff_avg or eff_avg <= 0) and amount_in_used and out_val:
                            try:
                                # First hop transforms BASE0 -> QUOTE0. Effective unit price (quote/base)
                                # approx = (out_quote) / (in_base)
                                eff_avg = float(out_val) / float(amount_in_used)
                            except Exception:
                                eff_avg = 0.0
                        if eff_avg and eff_avg > 0:
                            # Normalize to (first_hop_quote per first_hop_base)
                            if not invert:
                                first_hop_unit_price_q_per_b = eff_avg
                            else:
                                first_hop_unit_price_q_per_b = (1.0 / eff_avg)
                        first_hop_out_amount = float(out_val)
                    except Exception:
                        pass

            # Result summary: if start and end currencies coincide, delta is meaningful; otherwise report 0 delta
            amount_in_final = float(amount_in_used or 0.0)
            is_rt = (start_ccy == end_ccy)
            delta = (amount_cur - amount_in_final) if is_rt else 0.0
            status = "ok"
            ok_flag = True
            # Promote mirror observability to top-level details for simpler grepping
            mirror_meta: Dict[str, object] = {}
            try:
                if self.roundtrip_mirror_last_leg and is_rt and fills:
                    last_fill = fills[-1]
                    if bool(last_fill.get("mirror_last_leg")):
                        mlp = float(last_fill.get("mirror_limit_price") or 0.0)
                        lsym = str(last_fill.get("last_symbol") or "")
                        lside = str(last_fill.get("last_side") or "")
                        mirror_meta = {
                            "mirror_limit_price": mlp,
                            "last_symbol": lsym,
                            "last_side": lside,
                        }
                        # Detect mirror pending (last hop limit placed but effectively not filled)
                        try:
                            out_last = float(last_fill.get("amount_out") or 0.0)
                        except Exception:
                            out_last = 0.0
                        # Treat as pending when only dust was realized on the last hop.
                        # Use a threshold relative to the initial amount to ignore pre-existing dust balances.
                        # Example: if we started with 0.00015 BTC and ended with 0.00000085 BTC due to an unfilled mirror,
                        # classify as pending instead of a realized negative delta.
                        pending_threshold_units = max(1e-12, 0.05 * float(amount_in_final or 0.0))
                        if out_last <= pending_threshold_units:
                            status = "mirror_pending"
                            ok_flag = False
                            # Option 1 (default): neutralize delta so dashboards don't show realized loss
                            delta = 0.0
                            # Optionally compute mark-to-market estimate in start_ccy
                            try:
                                sym = str(last_fill.get("symbol") or "")
                                side = str(last_fill.get("last_side") or "")
                                # We assume two-hop common case: we currently hold the quote from hop 1
                                # amount we hold approximately equals first_hop_out_amount
                                held_est_q = float(first_hop_out_amount or 0.0)
                                m2m_delta = None
                                if sym and held_est_q > 0 and side == "buy":
                                    t = ex.fetch_ticker(sym)
                                    px = float(t.get("ask") or t.get("last") or t.get("bid") or 0.0)
                                    if px > 0:
                                        # Convert quote -> base estimate
                                        m2m_out_b = held_est_q / px
                                        m2m_delta = float(m2m_out_b - amount_in_final)
                                if m2m_delta is not None:
                                    mirror_meta["m2m_delta_estimate"] = float(m2m_delta)
                            except Exception:
                                pass
            except Exception:
                mirror_meta = {}
            # Guardrail: never mark ok if round-trip ends negative (only if not mirror pending)
            if is_rt and status != "mirror_pending" and delta < 0:
                ok_flag = False
                status = "failed"
            return SwapResult(
                ok_flag,
                status,
                amount_in_final,
                amount_cur,
                delta,
                {
                    "fills": fills,
                    "exchange": ex_id,
                    "start_ccy": start_ccy,
                    "final_ccy": cur_ccy,
                    **mirror_meta,
                    "sizing": {
                        **({"mode": ("auto" if sizing_meta.get("mode") else "manual")} if isinstance(sizing_meta, dict) else {}),
                        **({k: float(v) for k, v in (sizing_meta.items() if isinstance(sizing_meta, dict) else [])}),
                        "first_cap_units": float(first_cap or 0.0),
                    },
                },
            )
        except Exception as e:
            amount_in_final = float(amount_in_used or 0.0) if 'amount_in_used' in locals() else 0.0
            # On failure, report neutral out/in and zero delta to avoid unit-mismatch confusion
            return SwapResult(
                False,
                "failed",
                amount_in_final,
                amount_in_final,
                0.0,
                {"error": str(e), "fills": fills, "cur_ccy": cur_ccy},
            )


def _main_cli():
    import argparse
    import sys
    parser = argparse.ArgumentParser(description="Swapper: isolated swap executor")
    parser.add_argument("--config", type=str, default=str(paths.PROJECT_ROOT / "swapper.yaml"))
    parser.add_argument("--bf_line", type=str, default=None, help="BF line from radar to parse into a plan")
    parser.add_argument("--exchange", type=str, default=None, help="Exchange id if not using --bf_line")
    parser.add_argument("--path", type=str, default=None, help="Hop path like A->B->C->A if not using --bf_line")
    # --anchor is deprecated here; kept for backward-compat but ignored in execution
    parser.add_argument("--anchor", type=str, default=None)
    parser.add_argument("--amount", type=float, default=0.0)
    args = parser.parse_args()

    sw = Swapper(config_path=args.config)
    if args.bf_line:
        plan = sw.plan_from_bf_line(args.bf_line)
        if not plan:
            print("Invalid --bf_line")
            sys.exit(2)
    else:
        if not args.path:
            print("Provide --bf_line or --path")
            sys.exit(2)
        # In test mode, default exchange from config if not provided
        ex_default = None
        if sw.mode == "test":
            try:
                ex_default = (sw.config.get("test_exchange") or "binance") if isinstance(sw.config, dict) else "binance"
            except Exception:
                ex_default = "binance"
        ex_id = args.exchange or ex_default
        if not ex_id:
            print(
                "Exchange is required in real mode. Provide --exchange or use mode=test with test_exchange in config."
            )
            sys.exit(2)
        hops = [SwapHop(base=p, quote=q) for p, q in zip(args.path.split("->"), args.path.split("->")[1:])]
        # In test mode, choose the configured min amount per exchange if not explicitly provided
        if sw.mode == "test":
            default_amt = float(sw.test_min_amounts.get(_normalize_ccxt_id(ex_id), 1.0))
            amt = float(args.amount) if args.amount else default_amt
        else:
            amt = float(args.amount or 0.0)
    plan = SwapPlan(exchange=ex_id, hops=hops, amount=amt)

    # Log start (include units if possible)
    try:
        path_nodes = ("->".join([plan.hops[0].base] + [h.quote for h in plan.hops]) if plan.hops else (args.path or ""))
        amt = float(getattr(plan, "amount", 0.0) or 0.0)
        unit = plan.hops[0].base if (plan and plan.hops) else ""
        # Best-effort free balance for start currency
        bal_free = None
        try:
            if plan and plan.hops:
                start_ccy = plan.hops[0].base
                bal_free = SpotBalanceFetcher(timeout_ms=sw.timeout_ms).get_balance(plan.exchange, start_ccy)
        except Exception:
            bal_free = None
        sizing_note = ""
        try:
            scfg = sw.config.get("sizing") if isinstance(sw.config, dict) else None
            if isinstance(scfg, dict) and str((scfg.get("mode") or "")).lower() == "auto":
                sizing_note = f" | sizing=auto alpha={float(scfg.get('alpha_tob') or 0.0):.4f} beta={float(scfg.get('beta_dv_pct') or 0.0):.4f} min_usd={float(scfg.get('min_usd') or 0.0):.2f} max_usd={float(scfg.get('max_usd') or 0.0):.2f}"
        except Exception:
            sizing_note = ""
        zero_bal_note = (" | note=zero-free-balance" if (bal_free is not None and float(bal_free) <= 0.0) else "")
        logger.info(
            "start | config=%s | mode=%s | order_type=%s | tif=%s | exchange=%s | path=%s | amount_cap=%.8f %s | balance_free=%s %s%s%s",
            args.config,
            sw.mode,
            sw.order_type,
            sw.time_in_force,
            plan.exchange,
            path_nodes,
            amt,
            unit,
            (f"{float(bal_free):.8f}" if bal_free is not None else "n/a"),
            unit,
            sizing_note,
            zero_bal_note,
        )
    except Exception:
        pass

    res = sw.run(plan)

    # Log result summary (neutral on failure). Include reason and mirror observability if available.
    try:
        reason = None
        error_text = None
        try:
            if isinstance(res.details, dict):
                d = res.details
                reason = d.get("reason") or (d.get("error") and "error")
                # Preserve exact error text when present
                if d.get("error"):
                    try:
                        error_text = str(d.get("error"))
                    except Exception:
                        error_text = None
        except Exception:
            reason = None
        # Unit for amount_used
        try:
            start_unit = ""
            if isinstance(res.details, dict) and res.details.get("start_ccy"):
                start_unit = str(res.details.get("start_ccy"))
            elif plan and plan.hops:
                start_unit = plan.hops[0].base
        except Exception:
            start_unit = ""
        # Optional mirror debugging fields
        mirror_suffix = ""
        m2m_suffix = ""
        try:
            if isinstance(res.details, dict):
                mlp = res.details.get("mirror_limit_price")
                lsym = res.details.get("last_symbol")
                lside = res.details.get("last_side")
                m2m = res.details.get("m2m_delta_estimate")
                if (mlp is not None) or lsym or lside:
                    mlp_f = 0.0
                    try:
                        mlp_f = float(mlp or 0.0)
                    except Exception:
                        mlp_f = 0.0
                    mirror_suffix = f" | mirror: {str(lsym or '')} {str(lside or '')} limit={mlp_f:.8f}"
                if m2m is not None:
                    try:
                        m2m_f = float(m2m)
                        m2m_suffix = f" | m2m_delta={m2m_f:.8f}"
                    except Exception:
                        m2m_suffix = ""
        except Exception:
            mirror_suffix = ""
            m2m_suffix = ""
        # Sizing suffix
        sizing_suffix = ""
        try:
            if isinstance(res.details, dict):
                sz = res.details.get("sizing") or {}
                if isinstance(sz, dict) and sz.get("mode"):
                    sizing_suffix = (
                        f" | sizing={str(sz.get('mode'))} cap={float(sz.get('first_cap_units') or 0.0):.8f}"
                        f" usd={float(sz.get('target_usd') or 0.0):.2f} est_px={float(sz.get('est_usd_price') or 0.0):.6f}"
                    )
        except Exception:
            sizing_suffix = ""
        if reason:
            logger.info(
                "result | ok=%s | status=%s | in=%.8f | out=%.8f | delta=%.8f | exchange=%s | hops=%d | amount_used=%.8f %s | reason=%s%s%s%s%s",
                res.ok,
                res.status,
                res.amount_in,
                res.amount_out,
                res.delta,
                plan.exchange,
                len(plan.hops or []),
                float(res.amount_in or 0.0),
                start_unit,
                reason,
                mirror_suffix,
                (f" | error={error_text}" if error_text else ""),
                m2m_suffix,
                sizing_suffix,
            )
        else:
            logger.info(
                "result | ok=%s | status=%s | in=%.8f | out=%.8f | delta=%.8f | exchange=%s | hops=%d | amount_used=%.8f %s%s%s%s",
                res.ok,
                res.status,
                res.amount_in,
                res.amount_out,
                res.delta,
                plan.exchange,
                len(plan.hops or []),
                float(res.amount_in or 0.0),
                start_unit,
                mirror_suffix,
                m2m_suffix,
                sizing_suffix,
            )
    except Exception:
        pass
    print(
        {
            "ok": res.ok,
            "status": res.status,
            "amount_in": res.amount_in,
            "amount_out": res.amount_out,
            "delta": res.delta,
            "details": res.details,
        }
    )


# Backward-compat alias for callers that may import Swaper
Swaper = Swapper


if __name__ == "__main__":
    _main_cli()
