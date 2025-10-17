# Diagrama de Flujo del Motor de Arbitraje

Este diagrama describe el flujo completo de datos y ejecución del sistema de arbitraje, siguiendo las mejores prácticas de documentación recomendadas para proyectos Python.

```plaintext
[Exchange API]
  |  (ccxt descarga tickers de Binance)
  |  --> src/arbitraje/engine_techniques.py
  |  Entrada:
  |  {
  |    "BTC/USDT": {"bid": 60000, "ask": 60010},
  |    "ETH/USDT": {"bid": 3500, "ask": 3510},
  |    ...
  |  }
  |  Test: test_sanity.py
  |  Log: logs/exchange_download.log
  v
[Descarga de Tickers]
  |  --> src/arbitraje/engine_techniques.py
  |  Entrada: tickers (dict)
  |  Salida: tickers normalizados (dict)
  |  Test: test_sanity.py
  |  Log: logs/tickers_normalization.log
  v
[Construcción de Grafo]
  |  --> src/arbitraje/engine_techniques.py
  |  Entrada: tickers normalizados
  |  Salida: grafo de oportunidades (aristas, nodos)
  |  Test: test_sanity.py
  |  Log: logs/graph_build.log
  v
[Bellman-Ford / Engine]
  |  --> src/arbitraje/bf_numba_impl.py
  |      src/arbitraje/engine_techniques.py
  |  Entrada: grafo de oportunidades
  |  Salida: ciclos de arbitraje detectados (paths, profit)
  |  Test: test_sanity.py
  |  Log: logs/bf_run.log
  v
[Resultados en CSV]
  |  --> src/arbitraje/arbitrage_report_ccxt.py
  |  Entrada: ciclos de arbitraje
  |  Salida: arbitrage_bf_usdt_ccxt.csv (paths, profit, timestamp)
  |  Test: test_sanity.py
  |  Log: logs/csv_persistence.log
  v
[Radar / Swapper / Reporte]
  |  --> src/arbitraje/arbitrage_report_ccxt.py
  |  Entrada: arbitrage_bf_usdt_ccxt.csv
  |  Salida: visualización, alertas, paths para swapper
  |  Test: test_sanity.py
  |  Log: logs/radar_swaps.log
      |
      v
[Swapper]
  |  --> src/arbitraje/swapper.py (o llamado desde arbitrage_report_ccxt.py)
  |  Entrada: paths y oportunidades desde CSV
  |  Salida: ejecución de swaps en el exchange, logs de swaps, actualizaciones en CSV
  |  Test: test_sanity.py
  |  Log: logs/swapper.log
      |
      v
[Engine Loop]
  |  --> src/arbitraje/arbitrage_report_ccxt.py (main loop)
  |  Entrada: max_iters, config, modo de operación
  |  Salida: repite todo el pipeline anterior, recolecta y actualiza resultados
  |  Test: test_sanity.py
  |  Log: logs/engine_loop.log
```

---

Este archivo puede ser referenciado desde el README principal y los módulos para entender el flujo y la arquitectura del sistema.
