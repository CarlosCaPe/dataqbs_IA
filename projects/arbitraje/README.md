# Arbitraje
> Consulta el diagrama de flujo completo aquí: [docs/flujo_arbitraje.md](docs/flujo_arbitraje.md)

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



Version: 1.5.0 HUNTER (engine 3.0)
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
## Diagrama de Flujo de Tests

Actualmente solo existe un test principal de sanidad:

`test_sanity.py`: Verifica que el entorno de ejecución y la configuración básica están correctos.

No existen tests legacy ni de equivalencia Numba en el flujo principal. El diagrama y la documentación han sido actualizados para reflejar esto.

Para pruebas funcionales y de integración, consulta los scripts y módulos principales en `src/arbitraje/`.

Select with `--balance_provider`:
## Descripción General



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
- **engine_techniques.py**: Orquesta la conexión, descarga, normalización y grafo.
- **bf_numba_impl.py**: Algoritmo Bellman-Ford acelerado para detección de ciclos.
- **arbitrage_report_ccxt.py**: CLI principal, persistencia, reporte y loop de iteraciones.
- **swapper.py**: Ejecuta swaps en el exchange usando las oportunidades detectadas.

  threads: 0
- **test_engine_techniques.py**: Prueba todo el pipeline (descarga, normalización, grafo, persistencia, lectura, iteraciones).
- **test_bf_numba_equivalence.py**: Prueba la lógica y equivalencia del Bellman-Ford acelerado.
- **test_bf_migration.py**: Prueba migración y persistencia de ventanas de oportunidad.
- **test_swapper.py**: Prueba la ejecución y lógica del swapper (si existe).

  require_dual_quote: false
- Se generan logs en cada etapa crítica del flujo para auditoría y debugging:
  persist_top_csv: true
  revalidate_depth: true
  use_ws: true
  depth_levels: 20
  latency_penalty_bps: 0
  reset_history: true
  iter_timeout_sec: 0.0
max: 280

# ...otros parámetros generales...
- El loop principal (`arbitrage_report_ccxt.py`) controla la cantidad de iteraciones y la operación continua.
- El swapper se llama después de detectar y persistir oportunidades, ejecutando swaps reales en el exchange.

```
```python
{
  "BTC/USDT": {"bid": 60000, "ask": 60010},
  "ETH/USDT": {"bid": 3500, "ask": 3510},
  ...
}
```


- `arbitrage_bf_usdt_ccxt.csv` contiene:
**Ventajas:**
- Solo ventanas ejecutables en real (bid/ask y profundidad suficiente).
- Filtra hops de bajo volumen y rutas con slippage oculto.
- Permite muchas ventanas pequeñas y positivas.



**Riesgos:**
- Muy bajo riesgo de negativos; solo podrían aparecer por cambios abruptos en el libro entre escaneo y ejecución.

**Recomendación:**
- Usar como base y ajustar solo si se detectan negativos en la práctica.
- Para mayor seguridad, subir `min_quote_vol` o `min_net`.

Esta calibración es clave para el funcionamiento óptimo de GUILLERMO (memo).
---
