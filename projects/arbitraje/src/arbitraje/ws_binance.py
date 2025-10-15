from __future__ import annotations

import json
import threading
import time
from typing import Any, Dict, Optional

try:
    import websocket  # websocket-client
except Exception:  # pragma: no cover
    websocket = None


class BinanceL2PartialBook:
    """Maintains a partial L2 order book (depth20) for a single symbol via Binance WS.

    Notes:
    - Uses partial book stream (depth20@100ms) to avoid diff/merge complexity.
    - Provides last_book() with bids/asks [[price, qty], ...].
    - Reconnects on close/error with backoff.
    """

    def __init__(self, symbol: str, stream_interval_ms: int = 100):
        self.symbol = symbol.lower()
        self.stream_interval_ms = int(stream_interval_ms)
        self._ws: Optional[websocket.WebSocketApp] = None
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._last_book: Optional[Dict[str, Any]] = None
        self._last_t_rcv: float = 0.0
        self._stop = False

    def start(self):  # pragma: no cover
        if websocket is None:
            raise RuntimeError("websocket-client no instalado")
        if self._thread and self._thread.is_alive():
            return
        self._stop = False
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):  # pragma: no cover
        self._stop = True
        try:
            if self._ws:
                self._ws.close()
        except Exception:
            pass
        self._ws = None

    def last_book(self) -> Optional[Dict[str, Any]]:
        with self._lock:
            return self._last_book

    def latency_ms(self) -> Optional[float]:
        if self._last_t_rcv <= 0:
            return None
        return (time.time() - self._last_t_rcv) * 1000.0

    # internal
    def _run(self):  # pragma: no cover
        url = f"wss://stream.binance.com:9443/ws/{self.symbol}@depth20@{self.stream_interval_ms}ms"
        backoff = 1.0
        while not self._stop:
            try:
                self._ws = websocket.WebSocketApp(
                    url,
                    on_message=self._on_msg,
                    on_error=self._on_err,
                    on_close=self._on_close,
                )
                self._ws.on_open = self._on_open
                self._ws.run_forever(ping_interval=15, ping_timeout=5)
            except Exception:
                pass
            if self._stop:
                break
            time.sleep(backoff)
            backoff = min(30.0, backoff * 2.0)

    def _on_open(self, ws):  # pragma: no cover
        # reset backoff by recreating thread
        pass

    def _on_close(self, ws, *args):  # pragma: no cover
        pass

    def _on_err(self, ws, err):  # pragma: no cover
        # log suppressed here; tri_bot logs higher-level metrics
        pass

    def _on_msg(self, ws, msg):  # pragma: no cover
        self._last_t_rcv = time.time()
        try:
            data = json.loads(msg)
            # Expect keys: 'bids', 'asks'
            bids = data.get('bids') or []
            asks = data.get('asks') or []
            if bids and asks:
                with self._lock:
                    self._last_book = {"bids": bids, "asks": asks}
        except Exception:
            pass
