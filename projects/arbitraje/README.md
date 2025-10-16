# Arbitraje

Version: 1.3.0 (engine 3.0)

Nota rápida sobre la estructura del código:

- La implementación canónica del CLI y la lógica principal se encuentra en:

  `projects/arbitraje/src/arbitraje/arbitrage_report_ccxt.py`

- No crear copias del fichero `arbitrage_report_ccxt.py` en otras rutas. Si necesitas reorganizar
  el código o mover la implementación, edita el archivo canónico y actualiza los consumidores.

- Históricamente existía un "shim" en una ruta nidificada que re-exportaba el módulo canónico
  para mantener compatibilidad. Ese shim se ha eliminado para evitar confusión y duplicación.

Buenas prácticas:
- Si es necesario mantener compatibilidad por un periodo de transición, crea un shim muy
  pequeño que documente claramente su propósito (pero evita mantener lógica duplicada).
- Añade tests que importen el módulo desde la ruta esperada para detectar roturas de compatibilidad.

Gracias por mantener el repositorio limpio.
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

## Connector diagnostics (recommended)

Before running the radar or production scans, validate connector health. From the `projects/arbitraje` directory run:

```
cd projects/arbitraje
poetry install
poetry run python tests/scripts/test_connector_fetch.py
poetry run python scripts/diagnose_ticker_fetch.py
```

The diagnostic script includes environment checks and will show a clear error if SDKs are missing or if you run it from the repo root. Always run these commands inside the `projects/arbitraje` Poetry environment to avoid false negatives.

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

---
## Calibración recomendada para GUILLERMO (memo)

Esta configuración está optimizada para maximizar el volumen de ventanas pequeñas y positivas, minimizando el riesgo de negativos en ejecución real. Es el punto de partida recomendado para calibrar el sistema de arbitraje GUILLERMO (memo).

```yaml
mode: bf
ex: [binance, bitget, mexc, okx]
quote: USDT
inv: 0.0  # Siempre usa wallet; no asume inversión extra
bf:
  allowed_quotes: [USDT, USDC]
  fee: 0.10
  rank_by_qvol: true
  currencies_limit: 500
  min_net: 0.05
  min_net_per_hop: 0.00
  top: 40
  require_quote: true
  require_topofbook: true
  min_quote_vol: 5000
  min_hops: 3
  max_hops: 6
  threads: 0
  require_dual_quote: false
  persist_top_csv: true
  revalidate_depth: true
  use_ws: true
  depth_levels: 20
  latency_penalty_bps: 0
  reset_history: true
  iter_timeout_sec: 0.0
max: 280
# ...otros parámetros generales...
```

**Ventajas:**
- Solo ventanas ejecutables en real (bid/ask y profundidad suficiente).
- Filtra hops de bajo volumen y rutas con slippage oculto.
- Permite muchas ventanas pequeñas y positivas.
- Evita rutas con pares problemáticos (blacklist).

**Riesgos:**
- Muy bajo riesgo de negativos; solo podrían aparecer por cambios abruptos en el libro entre escaneo y ejecución.

**Recomendación:**
- Usar como base y ajustar solo si se detectan negativos en la práctica.
- Para mayor seguridad, subir `min_quote_vol` o `min_net`.

Esta calibración es clave para el funcionamiento óptimo de GUILLERMO (memo).
---
