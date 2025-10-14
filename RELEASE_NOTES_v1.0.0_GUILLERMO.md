# v1.0.0 — GUILLERMO (2025-10-14)

This is the first major release 1.0.0 labeled as GUILLERMO. It finalizes the radar + swapper workflow and ships the non-blocking autoswap integration.

What’s new
- Radar (BF)
  - Injected a single non-blocking spawn to `arbitraje.swapper` right after logging each selected BF opportunity, so scanning never blocks.
  - History and snapshot logs are cleaner and more consistent; simulation summaries match actual iterations.
- Swapper
  - Live configuration in `projects/arbitraje/swapper.live.yaml` with `dry_run: false`, `order_type: market`, `time_in_force: IOC`, and `settle_sleep_ms: 300`.
  - Fast path-first execution using top-of-book with light ticker usage.
- Developer Experience
  - VS Code tasks to install dependencies, run scanner, and run BF quick iterations.
  - Clearer configuration precedence and environment loading for API keys.

Upgrade notes
- Ensure your `.env` has valid API keys for your exchanges. The radar will now spawn the swapper when opportunities are logged.
- To disable autoswap, remove or guard the single-line spawn inside `arbitrage_report_ccxt.py`.

Artifacts
- Logs under `artifacts/arbitraje/logs/`
- CSV outputs under `artifacts/arbitraje/outputs/`

Tag
- v1.0.0 (annotated) with message "GUILLERMO".
