# arbitraje

Crypto price arbitrage scanner using ccxt (market data) with intra-exchange triangular and Bellman–Ford modes.

- Source layout: `src/`
- Artifacts: `artifacts/arbitraje/{logs,outputs}`
- CLIs:
	- `arbitraje-ccxt` (main)
	- `arbitraje-report` (legacy CoinGecko demo)

## Configuration (.env)

We automatically load `.env` from the repo root and from `projects/arbitraje/.env`.

Start with Binance (only) by copying `.env.example` to `.env` and filling:

```
BINANCE_API_KEY=...
BINANCE_API_SECRET=...
```

You can later add other exchanges using the placeholders in `.env.example`.

See `docs/exchanges/` for per-exchange guides. Binance guide: `docs/exchanges/binance.md`.

## Usage

Install:

```
poetry install
```

Run Bellman–Ford on Binance only with balance-aware logging (read-only):

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

Outputs are written to `artifacts/arbitraje/outputs` (CSVs) and logs to `artifacts/arbitraje/logs`.
