from __future__ import annotations

import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Optional

import ccxt  # type: ignore

from .swapper import Swapper, SwapPlan, _normalize_ccxt_id, _parse_bf_line

logger = logging.getLogger("dispatcher")


class RadarDispatcher:
    """Dispatch BF opportunities to Swapper with concurrency and safety gates.

    Features:
    - Threaded execution; one worker per window (opportunity).
    - Uses real wallet balance for the anchor currency as input amount.
    - Per-exchange min-amount gating and per-exchange concurrency (semaphore).
    - Emergency lever: pause dispatch per exchange on first negative realized delta.
    """

    def __init__(
        self,
        swapper_config_path: str,
        max_workers: int = 8,
        per_exchange_concurrency: int = 1,
        min_amounts: Optional[Dict[str, float]] = None,
        emergency_on_negative: bool = True,
        emergency_cooldown_sec: float = 0.0,
        balance_kind: str = "free",
        timeout_ms: int = 15000,
    ) -> None:
        self._tp = ThreadPoolExecutor(max_workers=max(1, int(max_workers)))
        self._semaphores: Dict[str, threading.Semaphore] = {}
        self._per_exchange_concurrency = max(1, int(per_exchange_concurrency))
        self._min_amounts = {str(k).lower(): float(v) for k, v in (min_amounts or {}).items()}
        self._emergency_on_negative = bool(emergency_on_negative)
        self._emergency_cooldown_sec = float(emergency_cooldown_sec or 0.0)
        self._paused: Dict[str, float] = {}  # ex_id -> ts when paused (epoch seconds) [placeholder]
        self._balance_kind = balance_kind if balance_kind in ("free", "total") else "free"
        self._timeout_ms = int(timeout_ms)
        self._swapper = Swapper(config_path=swapper_config_path)

    def submit_bf_line(self, bf_line: str) -> None:
        parsed = _parse_bf_line(bf_line)
        if not parsed:
            return
        ex_id, nodes, _hops, anchor = parsed
        ex_id = _normalize_ccxt_id(ex_id)
        if self._is_paused(ex_id):
            logger.debug("dispatcher: exchange %s paused; skipping", ex_id)
            return
        sem = self._semaphores.get(ex_id)
        if sem is None:
            sem = threading.Semaphore(self._per_exchange_concurrency)
            self._semaphores[ex_id] = sem
        try:
            sem.acquire(blocking=False)
        except Exception:
            # Shouldn't happen; fallback to non-blocking check
            if not sem.acquire(blocking=False):
                return
        # Build plan with amount=0. Swapper will use provided amount in run() call after we set it.
        plan = self._swapper.plan_from_bf_line(bf_line, amount=0.0)
        if not plan:
            sem.release()
            return
        # Submit worker
        self._tp.submit(self._worker, sem, ex_id, anchor, plan)

    def _worker(self, sem: threading.Semaphore, ex_id: str, anchor: str, plan: SwapPlan) -> None:
        try:
            amt = self._read_anchor_balance(ex_id, anchor)
            min_amt = float(self._min_amounts.get(ex_id, 1.0))
            if amt <= 0 or amt < min_amt:
                logger.debug(
                    "dispatcher: skip ex=%s anchor=%s: balance %.8f < min %.4f",
                    ex_id,
                    anchor,
                    amt,
                    min_amt,
                )
                return
            plan.amount = float(amt)
            res = self._swapper.run(plan)
            logger.info("dispatcher: swap ex=%s status=%s delta=%.8f", ex_id, res.status, res.delta)
            if self._emergency_on_negative and res.ok and res.delta < 0:
                # Pause this exchange; basic lever (no timed resume in v1)
                logger.warning("dispatcher: emergency pause ex=%s due to negative delta=%.8f", ex_id, res.delta)
                self._paused[ex_id] = 1.0  # mark as paused (value not used in v1)
        except Exception as e:
            logger.exception("dispatcher: worker error ex=%s: %s", ex_id, e)
        finally:
            try:
                sem.release()
            except Exception:
                pass

    def _read_anchor_balance(self, ex_id: str, anchor: str) -> float:
        try:
            cls = getattr(ccxt, ex_id)
            ex = cls({"enableRateLimit": True})
            # Auth creds via env are loaded by Swapper on import; ccxt will pick them up if env vars are present
            # Prefer authenticated: use Swapper helper to load auth instance
        except Exception:
            ex = None
        # Prefer using Swapper's loader to respect options like OKX defaultType and market buy behavior
        try:
            from .swapper import _load_exchange  # local import to avoid circular at module import time
            ex = _load_exchange(ex_id, auth=True, timeout_ms=self._timeout_ms)
        except Exception:
            pass
        if not ex:
            return 0.0
        try:
            bal = ex.fetch_balance()
            bucket = bal.get(self._balance_kind) or {}
            return float(bucket.get(anchor.upper(), 0.0) or 0.0)
        except Exception:
            return 0.0

    def _is_paused(self, ex_id: str) -> bool:
        return ex_id in self._paused
