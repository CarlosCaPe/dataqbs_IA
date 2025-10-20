from __future__ import annotations

import os
from typing import Any, Dict

import ccxt  # type: ignore


def normalize_ccxt_id(ex_id: str) -> str:
    value = (ex_id or "").strip().lower()
    aliases = {"gateio": "gate", "okex": "okx", "coinbasepro": "coinbase", "huobipro": "htx"}
    return aliases.get(value, value)


def creds_from_env(ex_id: str) -> Dict[str, Any]:
    env = os.environ
    ex_id = normalize_ccxt_id(ex_id)
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
            k = env.get("GATEIO_API_KEY") or env.get("GATE_API_KEY")
            s = env.get("GATEIO_API_SECRET") or env.get("GATE_API_SECRET")
            if k and s:
                return {"apiKey": k, "secret": s}
        elif ex_id == "mexc":
            k, s = env.get("MEXC_API_KEY"), env.get("MEXC_API_SECRET")
            if k and s:
                return {"apiKey": k, "secret": s}
    except Exception:
        pass
    return {}


def load_exchange(ex_id: str, auth: bool, timeout_ms: int = 15000) -> ccxt.Exchange:
    norm_id = normalize_ccxt_id(ex_id)
    cls = getattr(ccxt, norm_id)
    cfg: Dict[str, Any] = {"enableRateLimit": True}
    if auth:
        cfg.update(creds_from_env(norm_id))
    if norm_id == "okx":
        dt = os.environ.get("ARBITRAJE_OKX_DEFAULT_TYPE") or os.environ.get("OKX_DEFAULT_TYPE")
        if dt:
            opts = dict(cfg.get("options") or {})
            opts["defaultType"] = str(dt).strip().lower()
            cfg["options"] = opts
    if norm_id == "bitget":
        opts = dict(cfg.get("options") or {})
        opts["createMarketBuyOrderRequiresPrice"] = False
        cfg["options"] = opts
    if norm_id == "binance":
        opts = dict(cfg.get("options") or {})
        opts["createMarketBuyOrderRequiresPrice"] = False
        cfg["options"] = opts
    ex = cls(cfg)
    try:
        ex.timeout = int(timeout_ms)
    except Exception:
        pass
    return ex
