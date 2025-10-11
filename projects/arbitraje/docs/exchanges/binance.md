# Binance API Guide (Spot)

This guide summarizes key points from the official Binance API docs and how our tool uses them.

Official base endpoints:
- https://api.binance.com
- https://api1.binance.com
- https://api2.binance.com
- https://api3.binance.com
- https://api4.binance.com

Notes:
- All responses are JSON.
- Timestamps are in milliseconds.
- Data is typically oldest first, newest last.

## HTTP Return Codes
- 4XX: client errors (malformed requests)
- 403: WAF limit violated
- 409: cancelReplace partially succeeds
- 429: rate limit violation (back off!)
- 418: auto-banned for repeatedly violating limits after 429
- 5XX: internal errors; execution status UNKNOWN (do not assume failure)

Error payload example:
```json
{"code": -1121, "msg": "Invalid symbol."}
```

## Rate Limits
- `/api/v3/exchangeInfo` includes `rateLimits` for `RAW_REQUESTS`, `REQUEST_WEIGHT`, and `ORDERS`.
- Response headers include `X-MBX-USED-WEIGHT-(interval)` and `X-MBX-ORDER-COUNT-(interval)`.
- On 429, back off to avoid 418 bans. Use Retry-After headers when present.
- Consider WebSockets for market data where possible (not used by our tool currently).

## Endpoint Security Types
- NONE: public
- MARKET_DATA: may require API key
- USER_STREAM: API key
- TRADE / MARGIN / USER_DATA: require API key + HMAC/RSA signature

SIGNED endpoints require:
- `timestamp` (ms)
- optional `recvWindow` (default 5000ms, max 60000ms)
- `signature` via HMAC-SHA256 (key = secretKey, value = query/body string) or RSA (PKCS#8)

## How our tool uses Binance
- For scanning (tri/BF), we use public market endpoints via ccxt: `load_markets`, `fetch_tickers`.
- For balance-aware logging (`--use_balance`), we call `fetch_balance()` with API keys.
- We do NOT place orders in this tool.

## Environment Variables
Set these in `.env`:
```
BINANCE_API_KEY=...
BINANCE_API_SECRET=...
```

We load `.env` from:
- Repo root: `.env`
- Project folder: `projects/arbitraje/.env`

## Running with Binance only
Example to scan BF on Binance only, using balance-aware logging (read-only):
```
poetry run arbitraje-ccxt --mode bf \
  --ex binance \
  --quote USDT \
  --bf_fee 0.10 \
  --bf_currencies_limit 25 \
  --bf_min_net 0.5 \
  --bf_top 10 \
  --bf_require_quote \
  --bf_min_hops 3 \
  --bf_max_hops 6 \
  --repeat 10 \
  --repeat_sleep 2 \
  --bf_threads 1 \
  --use_balance --balance_kind free
```

After verifying, you can add other exchanges by filling their keys in `.env` and listing them in `--ex`.
