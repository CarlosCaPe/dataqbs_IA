from __future__ import annotations

import logging
import os
import re
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import ccxt  # type: ignore
import yaml

from . import paths

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
    anchor: str
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


def _normalize_ccxt_id(ex_id: str) -> str:
    x = (ex_id or "").strip().lower()
    aliases = {"gateio": "gate", "okex": "okx", "coinbasepro": "coinbase", "huobipro": "htx"}
    return aliases.get(x, x)


def _creds_from_env(ex_id: str) -> dict:
    env = os.environ
    ex_id = _normalize_ccxt_id(ex_id)
    try:
        if ex_id == "binance":
            k, s = env.get("BINANCE_API_KEY"), env.get("BINANCE_API_SECRET")
            if k and s:
                return {"apiKey": k, "secret": s}
        elif ex_id == "bybit":
            k, s = env.get("BYBIT_API_KEY"), env.get("BYBIT_API_SECRET")
            if k and s:
                return {"apiKey": k, "secret": s}
        elif ex_id == "bitget":
            k, s, p = env.get("BITGET_API_KEY"), env.get("BITGET_API_SECRET"), env.get("BITGET_PASSWORD")
            if k and s and p:
                return {"apiKey": k, "secret": s, "password": p}
        elif ex_id == "coinbase":
            k, s, p = env.get("COINBASE_API_KEY"), env.get("COINBASE_API_SECRET"), env.get("COINBASE_API_PASSWORD")
            if k and s and p:
                return {"apiKey": k, "secret": s, "password": p}
        elif ex_id == "okx":
            k, s = env.get("OKX_API_KEY"), env.get("OKX_API_SECRET")
            p = env.get("OKX_API_PASSWORD") or env.get("OKX_PASSWORD")
            if k and s and p:
                return {"apiKey": k, "secret": s, "password": p}
        elif ex_id == "kucoin":
            k, s, p = env.get("KUCOIN_API_KEY"), env.get("KUCOIN_API_SECRET"), env.get("KUCOIN_API_PASSWORD")
            if k and s and p:
                return {"apiKey": k, "secret": s, "password": p}
        elif ex_id in ("gate", "gateio"):
            k = os.environ.get("GATEIO_API_KEY") or os.environ.get("GATE_API_KEY")
            s = os.environ.get("GATEIO_API_SECRET") or os.environ.get("GATE_API_SECRET")
            if k and s:
                return {"apiKey": k, "secret": s}
        elif ex_id == "mexc":
            k, s = env.get("MEXC_API_KEY"), env.get("MEXC_API_SECRET")
            if k and s:
                return {"apiKey": k, "secret": s}
    except Exception:
        pass
    return {}


def _load_exchange(ex_id: str, auth: bool, timeout_ms: int = 15000) -> ccxt.Exchange:
    ex_id = _normalize_ccxt_id(ex_id)
    cls = getattr(ccxt, ex_id)
    cfg = {"enableRateLimit": True}
    if auth:
        cfg.update(_creds_from_env(ex_id))
    if ex_id == "okx":
        dt = os.environ.get("ARBITRAJE_OKX_DEFAULT_TYPE") or os.environ.get("OKX_DEFAULT_TYPE")
        if dt:
            opts = dict(cfg.get("options") or {})
            opts["defaultType"] = str(dt).strip().lower()
            cfg["options"] = opts
    # Bitget: allow market buy without price by treating amount as cost
    if ex_id == "bitget":
        opts = dict(cfg.get("options") or {})
        opts["createMarketBuyOrderRequiresPrice"] = False
        cfg["options"] = opts
    ex = cls(cfg)
    try:
        ex.timeout = int(timeout_ms)
    except Exception:
        pass
    return ex


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
        ex, nodes, _hops, anchor = parsed
        hops = [SwapHop(base=nodes[i], quote=nodes[i+1]) for i in range(len(nodes)-1)]
        if self.mode == "test":
            # Use per-exchange test minimum if available; fallback to 1.0
            amt = float(amount) if amount else float(self.test_min_amounts.get(_normalize_ccxt_id(ex), 1.0))
        else:
            amt = float(amount or 0.0)
        return SwapPlan(exchange=ex, hops=hops, anchor=anchor, amount=amt, raw_line=line)

    def run(self, plan: SwapPlan) -> SwapResult:
        if self.mode == "test":
            return self._run_test(plan)
        return self._run_real(plan)

    def _run_test(self, plan: SwapPlan) -> SwapResult:
        ex_id = plan.exchange
        anchor = plan.anchor.upper()
        # In test mode, respect configured per-exchange minimum when present
        amt_in = float(self.test_min_amounts.get(_normalize_ccxt_id(ex_id), 1.0))
        try:
            ex = _load_exchange(ex_id, auth=False, timeout_ms=self.timeout_ms)
            ex.load_markets()
            a1, a2 = ("USDT", "USDC") if anchor == "USDT" else ("USDC", "USDT")
            t = ex.fetch_tickers()
            amt_mid = self._convert_amount_through_tickers(a1, a2, t, amt_in)
            if amt_mid is None:
                return SwapResult(False, "failed", amt_in, 0.0, -amt_in, {"reason": "no_ticker_a1_a2"})
            amt_out = self._convert_amount_through_tickers(a2, a1, t, amt_mid)
            if amt_out is None:
                return SwapResult(False, "failed", amt_in, 0.0, -amt_in, {"reason": "no_ticker_a2_a1"})
            delta = amt_out - amt_in
            status = "positive" if delta > 0 else ("negative" if delta < 0 else "ok")
            return SwapResult(True, status, amt_in, amt_out, delta, {
                "exchange": ex_id,
                "anchor": anchor,
                "round_trip": f"{a1}->{a2}->{a1}",
            })
        except Exception as e:
            return SwapResult(False, "failed", amt_in, 0.0, -amt_in, {"error": str(e)})

    def _convert_amount_through_tickers(
        self,
        from_ccy: str,
        to_ccy: str,
        tickers: dict,
        amount: float,
    ) -> Optional[float]:
        from_ccy = from_ccy.upper()
        to_ccy = to_ccy.upper()
        sym1 = f"{from_ccy}/{to_ccy}"
        sym2 = f"{to_ccy}/{from_ccy}"
        t1 = tickers.get(sym1)
        if t1:
            bid = t1.get("bid") or t1.get("last")
            if bid and bid > 0:
                return float(amount) * float(bid)
        t2 = tickers.get(sym2)
        if t2:
            ask = t2.get("ask") or t2.get("last")
            if ask and ask > 0:
                return float(amount) / float(ask)
        return None

    def _run_real(self, plan: SwapPlan) -> SwapResult:
        ex_id = plan.exchange
        ex = _load_exchange(ex_id, auth=True, timeout_ms=self.timeout_ms)
        try:
            markets = ex.load_markets()
        except Exception:
            markets = {}
        amt = float(plan.amount or 0.0)
        if amt <= 0:
            try:
                bal = ex.fetch_balance()
                bucket = bal.get("free") or bal.get("total") or {}
                amt = float(bucket.get(plan.anchor, 0.0) or 0.0)
            except Exception:
                amt = 0.0
        if amt <= 0:
            return SwapResult(False, "failed", 0.0, 0.0, 0.0, {"reason": "no_funds"})

        amount_cur = amt
        cur_ccy = plan.anchor.upper()
        fills: List[Dict[str, object]] = []
        try:
            for hop in plan.hops:
                base, quote = hop.base.upper(), hop.quote.upper()
                sym = f"{base}/{quote}"
                invert = False
                if sym not in markets:
                    sym2 = f"{quote}/{base}"
                    if sym2 not in markets:
                        return SwapResult(
                            False,
                            "failed",
                            amt,
                            amount_cur,
                            amount_cur - amt,
                            {"reason": "symbol_missing", "hop": f"{base}->{quote}"},
                        )
                    sym = sym2
                    invert = True

                # Determine trade side based on the actual market symbol orientation
                # sym_base/sym_quote refer to the ccxt market we will send the order to
                sym_base, sym_quote = (base, quote) if not invert else (quote, base)
                if cur_ccy == sym_base:
                    side = "sell"  # selling base to get quote
                elif cur_ccy == sym_quote:
                    side = "buy"   # buying base using quote we currently hold
                else:
                    return SwapResult(
                        False,
                        "failed",
                        amt,
                        amount_cur,
                        amount_cur - amt,
                        {"reason": "currency_mismatch", "cur": cur_ccy, "hop": f"{base}->{quote}", "sym": sym},
                    )

                # Fetch ticker and choose appropriate side price (bid for sell, ask for buy)
                try:
                    t = ex.fetch_ticker(sym)
                    if side == "sell":
                        price = t.get("bid") or t.get("last")
                    else:
                        price = t.get("ask") or t.get("last")
                except Exception:
                    price = None

                params = {}
                # For market orders, many exchanges ignore or reject timeInForce; don't set it
                order_type = "market"

                try:
                    buy_uses_cost = getattr(ex, "id", "").lower() == "bitget"
                except Exception:
                    buy_uses_cost = False
                try:
                    if side == "buy":
                        if buy_uses_cost:
                            # Pass quote cost directly; exchange option allows this
                            amount_param = amount_cur
                        elif price:
                            amount_param = amount_cur / float(price)  # base amount to buy
                        else:
                            amount_param = amount_cur
                    else:
                        amount_param = amount_cur  # selling current base amount
                except Exception:
                    amount_param = amount_cur

                if self.dry_run:
                    fill_price = float(price or 0.0) if price else 0.0
                    if side == "sell":
                        amount_next = amount_param * float(price or 1.0)  # base -> quote
                    else:
                        amount_next = amount_param  # quote -> base
                    fills.append(
                        {
                            "symbol": sym,
                            "side": side,
                            "amount_in": amount_cur,
                            "amount_out": amount_next,
                            "price": fill_price,
                            "simulated": True,
                        }
                    )
                    amount_cur = float(amount_next)
                    # Advance along the hop path currency regardless of symbol inversion
                    cur_ccy = quote
                    continue

                order = ex.create_order(
                    symbol=sym,
                    type=order_type,
                    side=side,
                    amount=amount_param,
                    price=None,
                    params=params,
                )
                time.sleep(0.2)
                try:
                    oid = order.get("id") if isinstance(order, dict) else None
                except Exception:
                    oid = None
                filled_out = None
                if oid:
                    try:
                        o2 = ex.fetch_order(oid, sym)
                        filled = float(o2.get("filled") or 0.0)
                        avg = float(o2.get("average") or o2.get("price") or (price or 0.0))
                        if side == "sell":
                            filled_out = filled * avg
                        else:
                            filled_out = filled
                    except Exception:
                        filled_out = None

                if filled_out is None:
                    if side == "sell":
                        filled_out = amount_param * float(price or 1.0)  # base -> quote
                    else:
                        # If amount_param was passed as quote cost (bitget), convert to base using price
                        if buy_uses_cost and price:
                            filled_out = float(amount_param) / float(price)
                        else:
                            filled_out = amount_param  # already a base amount

                fills.append(
                    {
                        "symbol": sym,
                        "side": side,
                        "amount_in": amount_cur,
                        "amount_out": filled_out,
                        "order_id": oid,
                    }
                )
                amount_cur = float(filled_out)
                # Advance along the hop path to the target currency of this hop
                cur_ccy = quote

            delta = amount_cur - amt
            status = "positive" if delta > 0 else ("negative" if delta < 0 else "ok")
            return SwapResult(True, status, amt, amount_cur, delta, {"fills": fills, "exchange": ex_id})
        except Exception as e:
            return SwapResult(False, "failed", amt, amount_cur, amount_cur - amt, {"error": str(e), "fills": fills})


def _main_cli():
    import argparse
    import sys
    parser = argparse.ArgumentParser(description="Swapper: isolated swap executor")
    parser.add_argument("--config", type=str, default=str(paths.PROJECT_ROOT / "swapper.yaml"))
    parser.add_argument("--bf_line", type=str, default=None, help="BF line from radar to parse into a plan")
    parser.add_argument("--exchange", type=str, default=None, help="Exchange id if not using --bf_line")
    parser.add_argument("--path", type=str, default=None, help="Hop path like A->B->C->A if not using --bf_line")
    parser.add_argument("--anchor", type=str, default="USDT")
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
        plan = SwapPlan(exchange=ex_id, hops=hops, anchor=args.anchor, amount=amt)

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
