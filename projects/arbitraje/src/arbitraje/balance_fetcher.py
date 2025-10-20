from __future__ import annotations

import threading
from typing import Dict

import ccxt  # type: ignore

from .exchange_utils import load_exchange as _load_exchange
from .exchange_utils import normalize_ccxt_id as _normalize_ccxt_id


class SpotBalanceFetcher:
    """Minimal read-only helper for spot balances."""

    def __init__(self, timeout_ms: int = 15000) -> None:
        self._timeout_ms = timeout_ms
        self._clients: Dict[str, ccxt.Exchange] = {}
        self._lock = threading.Lock()

    def _get_client(self, exchange_id: str) -> ccxt.Exchange:
        norm_id = _normalize_ccxt_id(exchange_id)
        with self._lock:
            client = self._clients.get(norm_id)
            if client:
                return client
            client = _load_exchange(norm_id, auth=True, timeout_ms=self._timeout_ms)
            try:
                client.load_markets()
            except Exception:
                pass
            self._clients[norm_id] = client
            return client

    def get_balance(self, exchange_id: str, asset: str) -> float:
        client = self._get_client(exchange_id)
        balances = None
        try:
            balances = client.fetch_balance({"type": "spot"})
        except Exception:
            balances = client.fetch_balance()
        asset_key = asset.upper()
        free_map = balances.get("free") if isinstance(balances, dict) else None
        if isinstance(free_map, dict) and asset_key in free_map:
            return float(free_map[asset_key])
        total_map = balances.get("total") if isinstance(balances, dict) else None
        if isinstance(total_map, dict) and asset_key in total_map:
            return float(total_map[asset_key])
        entry = balances.get(asset_key) if isinstance(balances, dict) else None
        if isinstance(entry, dict):
            for key in ("free", "total", "available", "balance"):
                value = entry.get(key)
                if value is not None:
                    return float(value)
        if isinstance(entry, (int, float)):
            return float(entry)
        return 0.0


def get_spot_balance(exchange_id: str, asset: str, timeout_ms: int = 15000) -> float:
    """Convenience wrapper when caching is not needed."""

    fetcher = SpotBalanceFetcher(timeout_ms=timeout_ms)
    return fetcher.get_balance(exchange_id, asset)
