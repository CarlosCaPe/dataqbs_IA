from __future__ import annotations

from typing import List, Dict

import requests

BASE_URL = "https://api.coinpaprika.com/v1"


def get_top_coin_ids(session: requests.Session, limit: int = 300) -> List[str]:
    """Return top coin ids by rank (max `limit`).
    Uses /tickers which includes rank and coin id (e.g., 'btc-bitcoin').
    """
    url = f"{BASE_URL}/tickers"
    resp = session.get(url, timeout=20)
    resp.raise_for_status()
    data = resp.json()
    # Filter active and sort by rank
    items = []
    for t in data:
        try:
            cid = t.get("id")
            rank = int(t.get("rank") or 0)
            if not cid or rank <= 0:
                continue
            items.append((rank, cid))
        except Exception:
            continue
    items.sort(key=lambda x: x[0])
    return [cid for _, cid in items[:limit]]


def get_markets_for_coin(session: requests.Session, coin_id: str) -> List[Dict]:
    """Return market rows for a coin from /coins/{id}/markets?quotes=USD.
    Row keys: coin, exchange, pair, price (USD float)
    """
    url = f"{BASE_URL}/coins/{coin_id}/markets"
    params = {"quotes": "USD"}
    resp = session.get(url, params=params, timeout=20)
    if resp.status_code != 200:
        return []
    markets = resp.json() or []
    out: List[Dict] = []
    for m in markets:
        try:
            # skip outliers if flagged
            if m.get("outlier") is True:
                continue
            ex_name = m.get("exchange_name") or m.get("exchange_id") or "?"
            pair = m.get("pair") or f"{m.get('base_symbol','')}/{m.get('quote_symbol','')}"
            price = None
            quotes = m.get("quotes") or {}
            usd = quotes.get("USD") if isinstance(quotes, dict) else None
            if isinstance(usd, dict):
                price = usd.get("price")
            if price is None:
                # fallback to price if present
                price = m.get("price")
            price = float(price)
            if not (price > 0):
                continue
            out.append({
                "coin": coin_id,
                "exchange": ex_name,
                "pair": pair,
                "price": price,
            })
        except Exception:
            continue
    return out
