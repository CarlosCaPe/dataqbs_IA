# arbitraje

Crypto price arbitrage scanner using ccxt (market data) with intra-exchange triangular and Bellman–Ford modes.

- Source layout: `src/`
- Artifacts: `artifacts/arbitraje/{logs,outputs}`
- CLIs:
	- `arbitraje-ccxt` (main)
	- `swapper` (módulo de swaps aislado)

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
	# Wallet balance is always used automatically when credentials are present
```

Outputs are written to `artifacts/arbitraje/outputs` (CSVs) and logs to `artifacts/arbitraje/logs`.

### Swapper (isolated executor)

Pruebas rápidas con round-trip entre estables (por ejemplo USDT↔USDC):

Test (no órdenes reales):

```
poetry run swapper --config .\swapper.yaml --exchange binance --path USDT->USDC->USDT --anchor USDT
```

Real (órdenes reales; usa .env con tus llaves):

```
poetry run swapper --config .\swapper.live.yaml --exchange binance --path USDT->USDC->USDT --anchor USDT --amount 10.0
```

Notas:
- En `swapper.live.yaml` `dry_run=false` ejecuta órdenes reales; úsalo con cantidades muy pequeñas.
- Binance requiere ~10 USDT mínimo para USDT/USDC por filtros de NOTIONAL.
- Bitget/MEXC suelen aceptar ~1.01 USDT; OKX ~1.0.

## Balance providers & API keys

This project can read balances via multiple providers:

- ccxt (default): generic provider
- native: exchange-specific REST (e.g., Binance native endpoints)
- connector/SDK: official SDKs (e.g., Binance Spot SDK, Bitget SDK)

Select with `--balance_provider`:

```
--balance_provider ccxt|native|connector|bitget_sdk
```

Environment variables per exchange (set in `.env`):

- Binance: `BINANCE_API_KEY`, `BINANCE_API_SECRET`
- Bitget: `BITGET_API_KEY`, `BITGET_API_SECRET`, `BITGET_PASSWORD`
- Bybit: `BYBIT_API_KEY`, `BYBIT_API_SECRET`
- Coinbase Advanced: `COINBASE_API_KEY`, `COINBASE_API_SECRET`, `COINBASE_API_PASSWORD`
- OKX: `OKX_API_KEY`, `OKX_API_SECRET`, `OKX_API_PASSWORD`
- KuCoin: `KUCOIN_API_KEY`, `KUCOIN_API_SECRET`, `KUCOIN_API_PASSWORD`
- Kraken: `KRAKEN_API_KEY`, `KRAKEN_API_SECRET`
- Gate.io: `GATEIO_API_KEY`, `GATEIO_API_SECRET` (also supports `GATE_API_KEY`/`GATE_API_SECRET`)
- MEXC: `MEXC_API_KEY`, `MEXC_API_SECRET`

Notes:
- Balance usage is always on; if balance is unavailable, the tool assumes 0 to avoid overstating profits.
- For `--simulate_from_wallet`, when wallet cannot be read, simulation starts at 0 (currency per `--simulate_prefer`).

## SDK bootstrap (optional)

We keep SDK metadata in `arbitraje.yaml` under `sdk:`. You can either use Git submodules (preferred, already configured) or clone/update SDKs into `./sdk/*` with the helper.

Submodules (preferred):

```
git submodule update --init --recursive
git submodule update --remote --merge   # to update later
```

Helper script (optional alternative):

```
poetry run python bootstrap_sdks.py
```

SDK references (cloned into `sdk/*` when using bootstrap):

- Binance: https://github.com/binance/binance-connector-python
- MEXC: https://github.com/mexcdevelop/mexc-api-sdk (docs: https://www.mexc.com/api-docs/spot-v3/introduction#api-library)
- Bitget: https://github.com/BitgetLimited/v3-bitget-api-sdk
- OKX: https://github.com/okxapi/python-okx
