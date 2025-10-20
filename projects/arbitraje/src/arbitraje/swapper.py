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
if not logger.handlers:
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    logger.addHandler(sh)
    try:
        paths.LOGS_DIR.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(paths.LOGS_DIR / "swapper.log", encoding="utf-8")
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
    anchor: Optional[str] = None
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
        # Execution tuning (optional; defaults are fastest)
        self.settle_sleep_ms = int(self.config.get("settle_sleep_ms", 0))
        self.confirm_fill = bool(self.config.get("confirm_fill", False))
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
        # Optional swap fraction (0..1) to apply to first-hop source funds
        try:
            env_frac = os.environ.get("SWAP_FRACTION")
            self.swap_fraction: Optional[float] = (float(env_frac) if env_frac not in (None, "", "null") else None)
        except Exception:
            self.swap_fraction = None

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
        return SwapPlan(exchange=ex, hops=hops, amount=amt, anchor=_anchor, raw_line=line)

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
            for idx, hop in enumerate(plan.hops):
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
        first_cap = float(plan.amount or 0.0)
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
            anchor_ccy = (plan.anchor or start_ccy).upper()
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
                    return SwapResult(
                        False,
                        "failed",
                        float(amount_in_used or 0.0),
                        amount_cur,
                        amount_cur - float(amount_in_used or 0.0),
                        {"reason": "symbol_missing", "hop": f"{base}->{quote}", "cur_ccy": cur_ccy},
                    )

                # Trade strictly in the hop direction (base -> quote)
                sym_base, sym_quote = (base, quote) if not invert else (quote, base)
                # If symbol is base/quote, we sell base; if symbol is quote/base, we buy quote using base
                side = "sell" if not invert else "buy"

                # Determine source funds from real wallet balance of the hop's base currency
                src_free = _free_balance(base)
                src_to_use = float(src_free)
                # Apply cap on first hop only
                if idx == 0 and first_cap > 0:
                    src_to_use = min(src_to_use, float(first_cap))
                # Apply optional fraction on the hop that returns to the anchor currency
                if hop.quote.upper() == anchor_ccy and isinstance(self.swap_fraction, (int, float)):
                    frac = float(self.swap_fraction)
                    try:
                        if frac < 0.0:
                            frac = 0.0
                        elif frac > 1.0:
                            frac = 1.0
                    except Exception:
                        pass
                    src_to_use = src_to_use * frac
                if src_to_use <= 0:
                    return SwapResult(
                        False,
                        "failed",
                        float(amount_in_used or 0.0),
                        amount_cur,
                        amount_cur - float(amount_in_used or 0.0),
                        {"reason": "no_funds_source", "source": base, "free": float(src_free)},
                    )

                params = {}
                # For market orders, many exchanges ignore or reject timeInForce; don't set it
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
                    fills.append(
                        {
                            "symbol": sym,
                            "side": side,
                            "amount_in": src_to_use,
                            "amount_out": amount_next,
                            "price": fill_price,
                            "hop_index": idx,
                            "simulated": True,
                        }
                    )
                    amount_cur = float(amount_next)
                    cur_ccy = quote
                    if amount_in_used is None:
                        amount_in_used = float(src_to_use)
                    continue

                # Capture first-hop input now for accurate reporting
                if amount_in_used is None:
                    amount_in_used = float(src_to_use)

                order_amount = amount_param
                if side == "buy" and buy_uses_cost and "quoteOrderQty" in params:
                    order_amount = None  # let exchange compute base from quote cost
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
                        "hop_index": idx,
                    }
                )

            # Result summary: if start and end currencies coincide, delta is meaningful; otherwise report 0 delta
            amount_in_final = float(amount_in_used or 0.0)
            delta = (amount_cur - amount_in_final) if (start_ccy == end_ccy) else 0.0
            status = "ok"
            return SwapResult(
                True,
                status,
                amount_in_final,
                amount_cur,
                delta,
                {"fills": fills, "exchange": ex_id, "start_ccy": start_ccy, "final_ccy": cur_ccy},
            )
        except Exception as e:
            amount_in_final = float(amount_in_used or 0.0) if 'amount_in_used' in locals() else 0.0
            return SwapResult(
                False,
                "failed",
                amount_in_final,
                amount_cur,
                amount_cur - amount_in_final,
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
    parser.add_argument("--fraction", type=float, default=None, help="Fraction (0..1) applied on the anchor hop (->anchor)")
    args = parser.parse_args()

    sw = Swapper(config_path=args.config)
    # Override swap fraction from CLI if provided
    if args.fraction is not None:
        try:
            sw.swap_fraction = float(args.fraction)
        except Exception:
            pass
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
        path_nodes = args.path.split("->")
        hops = [SwapHop(base=p, quote=q) for p, q in zip(path_nodes, path_nodes[1:])]
        # In test mode, choose the configured min amount per exchange if not explicitly provided
        if sw.mode == "test":
            default_amt = float(sw.test_min_amounts.get(_normalize_ccxt_id(ex_id), 1.0))
            amt = float(args.amount) if args.amount else default_amt
        else:
            amt = float(args.amount or 0.0)
    # Determine anchor: CLI --anchor wins; else if cycle, last equals first -> anchor is first; else default to first base
    anchor_cli = (args.anchor.upper() if args.anchor else None)
    inferred_anchor = None
    try:
        first_node = path_nodes[0].upper()
        last_node = path_nodes[-1].upper()
        inferred_anchor = first_node if last_node == first_node else first_node
    except Exception:
        pass
    anchor_final = anchor_cli or inferred_anchor
    plan = SwapPlan(exchange=ex_id, hops=hops, amount=amt, anchor=anchor_final)

    res = sw.run(plan)
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
