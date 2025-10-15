from __future__ import annotations

import hashlib
import hmac
import os
import time
from typing import Any, Dict, List, Optional

import requests

DEFAULT_BASES = [
    "https://api.binance.com",
    "https://api1.binance.com",
    "https://api2.binance.com",
    "https://api3.binance.com",
    "https://api4.binance.com",
]


def _now_ms() -> int:
    return int(time.time() * 1000)


def _build_bases() -> List[str]:
    # Allow override via env (comma-separated); else use defaults
    env_base = os.environ.get("BINANCE_API_BASE", "").strip()
    if env_base:
        return [env_base]
    return DEFAULT_BASES


def _sign_query(query_str: str, secret: str) -> str:
    mac = hmac.new(secret.encode("utf-8"), query_str.encode("utf-8"), hashlib.sha256)
    return mac.hexdigest()


def binance_request(
    method: str,
    path: str,
    params: Optional[Dict[str, Any]] = None,
    api_key: Optional[str] = None,
    api_secret: Optional[str] = None,
    signed: bool = False,
    recv_window_ms: int = 5000,
    timeout: int = 20_000,
) -> Any:
    """Make a Binance REST request across base endpoints with optional HMAC signing.

    - method: GET/POST/DELETE
    - path: e.g. "/sapi/v1/convert/exchangeInfo" or "/api/v3/account"
    - params: dict of query/body params
    - signed: include timestamp/recvWindow and signature
    - timeout: total request timeout in ms
    """
    params = dict(params or {})
    headers = {"Connection": "close"}
    if api_key:
        headers["X-MBX-APIKEY"] = api_key

    if signed:
        params.setdefault("timestamp", _now_ms())
        params.setdefault("recvWindow", recv_window_ms)

    # requests expects seconds; use explicit (connect, read) timeouts to avoid indefinite SSL reads
    timeout_s = max(1.0, float(timeout) / 1000.0)
    timeout_tuple = (timeout_s, timeout_s)

    # Build query string preserving order (Binance doesn't require specific order, but deterministic helps)
    def to_query(d: Dict[str, Any]) -> str:
        parts = []
        for k in sorted(d.keys()):
            v = d[k]
            parts.append(f"{k}={v}")
        return "&".join(parts)

    data = None
    query = to_query(params)
    if signed:
        if not api_secret:
            raise ValueError("signed=True requires api_secret")
        sig = _sign_query(query, api_secret)
        if method.upper() == "GET":
            query = f"{query}&signature={sig}" if query else f"signature={sig}"
        else:
            # for POST/DELETE we can send signature in body as well
            data = f"{query}&signature={sig}" if query else f"signature={sig}"
            query = None

    last_exc = None
    for base in _build_bases():
        url = f"{base}{path}"
        try:
            if method.upper() == "GET":
                r = requests.get(url, headers=headers, params=query, timeout=timeout_tuple)
            elif method.upper() == "POST":
                # application/x-www-form-urlencoded body
                r = requests.post(
                    url,
                    headers=headers,
                    data=data,
                    params=None if signed else params,
                    timeout=timeout_tuple,
                )
            elif method.upper() == "DELETE":
                r = requests.delete(
                    url,
                    headers=headers,
                    data=data,
                    params=None if signed else params,
                    timeout=timeout_tuple,
                )
            else:
                raise ValueError(f"Unsupported method: {method}")
            if r.status_code == 200:
                return r.json()
            # Raise to try next base when 5xx/429 etc.
            last_exc = RuntimeError(f"HTTP {r.status_code}: {r.text}")
        except Exception as e:
            last_exc = e
            continue
    # If we got here, all bases failed
    raise last_exc if last_exc else RuntimeError("Binance request failed")


def get_convert_pairs(
    api_key: str,
    api_secret: str,
    from_asset: Optional[str] = None,
    to_asset: Optional[str] = None,
    timeout: int = 20_000,
) -> Any:
    params: Dict[str, Any] = {}
    if from_asset:
        params["fromAsset"] = from_asset
    if to_asset:
        params["toAsset"] = to_asset
    # Convert exchangeInfo appears to be MARKET_DATA; API key recommended; signature not required
    return binance_request(
        "GET",
        "/sapi/v1/convert/exchangeInfo",
        params=params,
        api_key=api_key,
        api_secret=api_secret,
        signed=False,
        timeout=timeout,
    )


def get_convert_asset_info(api_key: str, api_secret: str, recv_window_ms: int = 5000, timeout: int = 20_000) -> Any:
    # USER_DATA -> signed
    return binance_request(
        "GET",
        "/sapi/v1/convert/assetInfo",
        params={},
        api_key=api_key,
        api_secret=api_secret,
        signed=True,
        recv_window_ms=recv_window_ms,
        timeout=timeout,
    )


def get_account_balances(api_key: str, api_secret: str, recv_window_ms: int = 5000, timeout: int = 20_000) -> Any:
    # Signed account info
    return binance_request(
        "GET",
        "/api/v3/account",
        params={},
        api_key=api_key,
        api_secret=api_secret,
        signed=True,
        recv_window_ms=recv_window_ms,
        timeout=timeout,
    )


def get_convert_quote(
    api_key: str,
    api_secret: str,
    from_asset: str,
    to_asset: str,
    from_amount: float,
    recv_window_ms: int = 5000,
    timeout: int = 20_000,
) -> Any:
    """Retrieve a Binance Convert quote for converting from_asset -> to_asset for a given amount.

    Notes:
    - Endpoint: POST /sapi/v1/convert/getQuote (USER_DATA)
    - Requires signed request with timestamp/recvWindow and signature.
    - from_amount is expressed in units of from_asset.
    - Response typically includes quotedPrice and toAmount; we don't enforce schema here.
    """
    params = {
        "fromAsset": str(from_asset).upper(),
        "toAsset": str(to_asset).upper(),
        "fromAmount": from_amount,
    }
    return binance_request(
        "POST",
        "/sapi/v1/convert/getQuote",
        params=params,
        api_key=api_key,
        api_secret=api_secret,
        signed=True,
        recv_window_ms=recv_window_ms,
        timeout=timeout,
    )
