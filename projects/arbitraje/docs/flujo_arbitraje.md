# Diagrama de Flujo del Motor de Arbitraje (v1.6.0 FISHER)

Vista de alto nivel del pipeline actual, artefactos, y puntos de instrumentación.

```plaintext
[Config/CLI]
  |  arbitraje.prod.yaml / CLI overrides (CLI > YAML > defaults)
  v
[Engine Main Loop]
  |  -> src/arbitraje/arbitrage_report_ccxt.py (modo: bf/tri/inter/...)
  |  - Escribe snapshot temprano (Progress/Headers) para observabilidad
  |  - [TIMING] logs por iteración (carga de exchange, markets, tickers, delegación)
  |  Artefactos (logs):
  |    artifacts/arbitraje/logs/current_bf.txt
  |    artifacts/arbitraje/logs/bf_history.txt
  v
[Per-Exchange Worker]
  |  -> ccxt.exchange(...)
  |  -> load_markets() (Opcional)
  |  -> fetch_tickers() o feeds
  |  -> Normalización + build de adyacencias
  |  -> Delegación a técnicas (engine_techniques) si aplica
  |     (puede dominar el tiempo total)
  |  [TIMING] ex: setup/markets/adj/currencies/tickers/delegate
  v
[Detección de oportunidades]
  |  -> BF/tri + filtros: volumen, top-of-book, hops, net, etc.
  |  -> Agrega por exchange + ranking
  v
[Persistencia de Resultados]
  |  -> artifacts/arbitraje/outputs/
  |     - arbitrage_bf_usdt_ccxt.csv (iteración)
  |     - arbitrage_bf_current_usdt_ccxt.csv (snapshot actual)
  |     - arbitrage_bf_simulation_usdt_ccxt.csv (por iteración)
  |     - arbitrage_bf_simulation_summary_usdt_ccxt.csv
  |     - arbitrage_bf_usdt_persistence.csv
  |     - bf_sim_summary.{csv,md}
  |  Logs/snapshots:
  |     - current_bf.txt: incluye sección [SIM] y resumen por exchange
  |     - bf_history.txt: append por iteración con [SIM]
  v
[Radar / Swapper]
  |  -> Lectura de CSVs y snapshot para decidir alertas/auto-swap
  |  -> swapper.yaml / swapper.live.yaml
```

Notas
- La sección [SIM] aparece en current_bf.txt y bf_history.txt, y en CSVs dedicados para entrenamiento.
- La delegación a técnicas puede ser el mayor contribuyente de tiempo por iteración; los [TIMING] ayudan a localizar cuellos de botella.
- El loop nunca hace `continue` antes de persistir; el sleep está dentro del ciclo y logueado.

Artefactos clave
- Logs: `artifacts/arbitraje/logs/*`
- Outputs: `artifacts/arbitraje/outputs/*`

Tests y validación
- Smoke: ejecución 1x iter para verificar headers, [SIM] y CSVs.
- Unit tests: equivalencia BF (payload) y CLI `--version`.
