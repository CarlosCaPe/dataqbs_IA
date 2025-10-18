# Arbitraje
Consulta el diagrama de flujo: [docs/flujo_arbitraje.md](docs/flujo_arbitraje.md)

Version: 1.6.0 FISHER (engine 3.2)

- Source layout: `src/`
- Artefactos: `artifacts/arbitraje/{logs,outputs}`
- CLIs:
  - `arbitraje-ccxt` (principal)
  - `swapper` (módulo de swaps aislado)

## Uso rápido

VS Code Tasks (Terminal > Run Task):
- Arbitraje: Validate build & tests
- Run BF (1 iter quick) — rápido para smoke-test con `arbitraje.prod.yaml`
- Arbitraje: Run CCXT (screen) / (prod)

CLI directo (desde `projects/arbitraje`):
- `poetry run python -m arbitraje.arbitrage_report_ccxt --mode bf --config .\arbitraje.prod.yaml --repeat 1`

Artefactos esperados tras 1 iteración (USDT):
- Logs: `artifacts/arbitraje/logs/current_bf.txt`, `bf_history.txt`
- CSVs: `artifacts/arbitraje/outputs/arbitrage_bf_current_usdt_ccxt.csv`, `arbitrage_bf_usdt_ccxt.csv`, `arbitrage_bf_simulation_usdt_ccxt.csv`, `arbitrage_bf_simulation_summary_usdt_ccxt.csv`, `arbitrage_bf_usdt_persistence.csv`, `bf_sim_summary.{csv,md}`

¿Dónde aparecen los [SIM]?
- En `current_bf.txt` (encabezado y resumen final) y en `bf_history.txt` (append por iteración).
- En CSV: `arbitrage_bf_simulation_usdt_ccxt.csv` y `arbitrage_bf_simulation_summary_usdt_ccxt.csv`.

## Configuración

Precedencia: CLI > YAML (`arbitraje.yaml` / `arbitraje.prod.yaml`) > defaults.

Variables de entorno por exchange (usar `.env` en repo y/o en `projects/arbitraje`):
- Binance: `BINANCE_API_KEY`, `BINANCE_API_SECRET`
- Bitget: `BITGET_API_KEY`, `BITGET_API_SECRET`, `BITGET_PASSWORD`
- Bybit: `BYBIT_API_KEY`, `BYBIT_API_SECRET`
- Coinbase Advanced: `COINBASE_API_KEY`, `COINBASE_API_SECRET`, `COINBASE_API_PASSWORD`
- OKX: `OKX_API_KEY`, `OKX_API_SECRET`, `OKX_API_PASSWORD`
- KuCoin: `KUCOIN_API_KEY`, `KUCOIN_API_SECRET`, `KUCOIN_API_PASSWORD`
- Kraken: `KRAKEN_API_KEY`, `KRAKEN_API_SECRET`
- Gate.io: `GATEIO_API_KEY`, `GATEIO_API_SECRET` (o `GATE_API_KEY`/`GATE_API_SECRET`)
- MEXC: `MEXC_API_KEY`, `MEXC_API_SECRET`

Balance y simulación:
- Si no hay credenciales o no se puede leer el wallet, el balance se trata como 0.
- `--simulate_from_wallet`: inicia desde wallet real o 0 (según disponibilidad), preferencia por `--simulate_prefer`.

## Instrumentación y observabilidad

- El loop escribe el snapshot temprano (Progress/Headers) en `current_bf.txt`.
- Marcadores `[TIMING]` por iteración y por exchange: setup, `load_markets`, `build_adjacency`, selección de monedas, `fetch_tickers`, delegación a técnicas.
- La delegación puede dominar el tiempo total; usa los `[TIMING]` para identificar cuellos de botella.

## SDK bootstrap (opcional)

Metadatos en `arbitraje.yaml` bajo `sdk:`. Preferir submódulos git:

```
git submodule update --init --recursive
git submodule update --remote --merge
```

Alternativa: `poetry run python bootstrap_sdks.py`

Referencias:
- Binance: https://github.com/binance/binance-connector-python
- MEXC: https://github.com/mexcdevelop/mexc-api-sdk
- Bitget: https://github.com/BitgetLimited/v3-bitget-api-sdk
- OKX: https://github.com/okxapi/python-okx

## Calibración recomendada (BF / USDT)

```yaml
mode: bf
ex: [binance, bitget, mexc, okx]
quote: USDT
inv: 0.0
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
```

## Estructura del código

- `arbitrage_report_ccxt.py`: CLI principal, loop de iteraciones, persistencia, reportes.
- `engine_techniques.py`: delegación de técnicas CPU-bound (BF/tri payload), proceso/timeout.
- `bf_numba_impl.py`: implementación BF acelerada (payload-aware).
- `swapper.py`: ejecución de swaps en exchanges.

Consejo: no dupliques `arbitrage_report_ccxt.py`; mantén la ruta canónica en `src/arbitraje`.
