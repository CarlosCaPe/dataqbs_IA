from __future__ import annotations

import json
import math

import ccxt  # type: ignore

EXS = ["binance", "okx", "bitget", "mexc"]
PAIR_CANDIDATES = ("USDC/USDT", "USDT/USDC")


def round_up(x: float, step: float | None) -> float:
    if not step or step <= 0:
        return float(x)
    return math.ceil(x / step) * step


def main() -> int:
    out = {}
    for exid in EXS:
        ex = getattr(ccxt, exid)({"enableRateLimit": True})
        try:
            markets = ex.load_markets()
        except Exception as e:
            out[exid] = {"error": str(e)}
            continue
        sym = None
        for cand in PAIR_CANDIDATES:
            if cand in markets:
                sym = cand
                break
        if not sym:
            out[exid] = {"symbol": None, "error": "no USDT/USDC market"}
            continue
        m = markets[sym]
        limits = (m.get("limits") or {})
        amount_min = (limits.get("amount") or {}).get("min")
        cost_min = (limits.get("cost") or {}).get("min")
        # quote precision isn't always provided; use price precision to round cost
        precision = m.get("precision") or {}
        price_prec = precision.get("price")
        # ccxt returns price precision as step, sometimes decimal places. Normalize if decimal places
        step = None
        if isinstance(price_prec, (int, float)):
            step = float(price_prec)
            if 0 < step < 1:
                # assume this is the step itself
                pass
            elif step >= 1:
                # assume decimal places
                step = 10 ** (-int(step)) if step <= 10 else None
        try:
            t = ex.fetch_ticker(sym)
            ask = float(t.get("ask") or t.get("last") or 1.0)
        except Exception:
            ask = 1.0
        # Required quote cost to satisfy both constraints
        need_cost = 0.0
        if cost_min:
            need_cost = max(need_cost, float(cost_min))
        if amount_min:
            need_cost = max(need_cost, float(amount_min) * ask)
        # Safety epsilon to avoid equality-edge rejects
        epsilon = 0.01 if exid in ("bitget", "mexc") else 0.0
        raw = need_cost + epsilon
        amt = round_up(raw, step)
        out[exid] = {
            "symbol": sym,
            "amount_min": amount_min,
            "cost_min": cost_min,
            "ask": ask,
            "recommended_amount": float(f"{amt:.8f}")
        }
    print(json.dumps(out, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
