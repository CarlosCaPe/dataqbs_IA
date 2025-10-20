# Release v0.4.1 — Swapper Alpha

Date: 2025-10-12

Highlights:
- Swapper Alpha: path-first execution (base->quote estrictamente), sin usar anchor en ejecución.
- Primer hop usa --amount como tope; si no se da, usa TODO el balance de la base; hops siguientes usan el balance real neto de fees.
- Optimizaciones de velocidad: selección de símbolo via markets precargados, fetch_ticker solo cuando es necesario, sin esperas automáticas por defecto.
- Config rápida actualizada: `swapper.yaml` con `settle_sleep_ms: 0`, `confirm_fill: false`; archivo `swapper.live.yaml` para órdenes reales (`dry_run: false`).
- Manejo de fees y balance libre entre hops (opcional confirm_fill=false para mayor velocidad).

Notes:
- Para Bitget/Binance, compras de mercado usan cost-based cuando aplica.
- CLI mantiene `--anchor` como no-op por compatibilidad; será removido en una versión futura.
