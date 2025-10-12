from __future__ import annotations
import json
import ccxt  # type: ignore

def main() -> int:
    exs = ["binance", "okx", "bitget", "mexc"]
    out = {}
    for exid in exs:
        ex = getattr(ccxt, exid)({"enableRateLimit": True})
        try:
            m = ex.load_markets()
        except Exception as e:
            out[exid] = {"error": str(e)}
            continue
        sym = None
        for cand in ("USDC/USDT", "USDT/USDC"):
            if cand in m:
                sym = cand
                break
        if not sym:
            out[exid] = {"symbol": None, "limits": None, "note": "No direct USDT<->USDC market"}
            continue
        info = m[sym]
        limits = info.get("limits") or {}
        out[exid] = {
            "symbol": sym,
            "limits": limits,
            "precision": info.get("precision"),
            "taker": info.get("taker"),
            "maker": info.get("maker"),
        }
    print(json.dumps(out, indent=2, default=str))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
