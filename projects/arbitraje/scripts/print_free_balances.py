import os
from pathlib import Path
from typing import Dict

try:
    from dotenv import load_dotenv
except Exception:
    load_dotenv = None  # type: ignore

import json
import ccxt  # type: ignore


def load_envs() -> None:
    if load_dotenv is None:
        return
    project_root = Path(__file__).resolve().parents[1]
    monorepo_root = project_root.parent.parent
    try:
        load_dotenv(dotenv_path=str(monorepo_root / ".env"), override=False)
    except Exception:
        pass
    try:
        load_dotenv(dotenv_path=str(project_root / ".env"), override=False)
    except Exception:
        pass


def creds_from_env(ex_id: str) -> Dict[str, str]:
    ex = ex_id.lower()
    e = os.environ
    if ex == "binance":
        k, s = e.get("BINANCE_API_KEY"), e.get("BINANCE_API_SECRET")
        return {"apiKey": k or "", "secret": s or ""}
    if ex == "okx":
        k, s = e.get("OKX_API_KEY"), e.get("OKX_API_SECRET")
        p = e.get("OKX_API_PASSWORD") or e.get("OKX_PASSWORD")
        return {"apiKey": k or "", "secret": s or "", "password": p or ""}
    if ex == "bitget":
        k, s, p = e.get("BITGET_API_KEY"), e.get("BITGET_API_SECRET"), e.get("BITGET_PASSWORD")
        return {"apiKey": k or "", "secret": s or "", "password": p or ""}
    if ex == "mexc":
        k, s = e.get("MEXC_API_KEY"), e.get("MEXC_API_SECRET")
        return {"apiKey": k or "", "secret": s or ""}
    return {}


def main() -> int:
    load_envs()
    out = {}
    for exid in ["binance", "okx", "bitget", "mexc"]:
        try:
            cfg = {"enableRateLimit": True}
            cfg.update({k: v for k, v in creds_from_env(exid).items() if v})
            if exid == "okx":
                # Ensure spot balances by default
                cfg.setdefault("options", {})
                cfg["options"]["defaultType"] = os.environ.get("ARBITRAJE_OKX_DEFAULT_TYPE", "spot")
            ex = getattr(ccxt, exid)(cfg)
            bal = ex.fetch_balance()
            free = bal.get("free") or {}
            out[exid] = {"free_USDT": float(free.get("USDT") or 0.0), "free_USDC": float(free.get("USDC") or 0.0)}
        except Exception as e:
            out[exid] = {"error": str(e)}
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
