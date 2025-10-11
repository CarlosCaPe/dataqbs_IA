# v0.1.0 – Versión estable

## Novedades principales

- Arbitraje (projects/arbitraje)
  - Escaneo multi-exchange con Bellman-Ford (ciclos de log-negativo) y simulador de composición por exchange (usa saldos reales por exchange).
  - Filtros de calidad: top-of-book, volumen por par/mercado, ranking por liquidez, anclajes USDT/USDC, límites de hops.
  - Rendimiento: caché de instancias/markets ccxt y modo thread-per-exchange para bajar latencia por iteración.
  - UX/Logs: sin limpiar consola (flag/env), logs persistentes con historial y snapshots por iteración; menos ruido en consola (oculta [SIM] redundante y avisos de SDK opcional).
  - Integraciones: ccxt por defecto, SDK oficiales opcionales (Binance/Bitget) con fallback seguro; cliente REST nativo para Binance para endpoints puntuales.

- Migraciones Telus → TLS
  - tls_compara_audios: automatización (Playwright) para comparativa de audios, heurísticas por headers/tamaño, CSV de auditoría y artefactos bajo artifacts/.
  - tls_compara_imagenes: runner migrado con rutas unificadas y shim de compatibilidad.

- Limpieza y deprecaciones
  - Limpieza de data/logs antiguos en real_estate.
  - supplier_verifier marcado como deprecado (estructura mínima y README).

- Infra de repo
  - Se formalizó projects/binance-connector-python como submódulo (branch master) en .gitmodules.

## Requisitos

- Python 3.11 recomendado (>=3.9,<3.14 para SDKs oficiales).
- Poetry para entornos por proyecto.
- Variables de entorno/API keys para exchanges cuando se use balance/operativa real.

## Cómo ejecutar (rápido)

- Arbitraje:
  - Instalar deps en projects/arbitraje con Poetry y ejecutar el CLI con los flags deseados (BF/simulación, filtros y anchors). Ver README del proyecto.
- TLS compare:
  - Instalar deps en projects/tls_compara_audios o projects/tls_compara_imagenes y ejecutar el runner; los artefactos se guardan bajo artifacts/.

## Notas

- Esta build prioriza spot/ccxt y la velocidad de escaneo; Convert/API avanzadas se mantienen opcionales.
- Los logs persistentes están en artifacts/arbitraje/logs/ y los outputs en artifacts/arbitraje/outputs/.
