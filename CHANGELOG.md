## 0.4.1 (2025-10-12)

Swapper Alpha
- Swapper sigue el path en orden (base->quote), sin depender de anchor.
- Primer hop cap por `--amount`; demás hops usan balance real neto de fees.
- Menos REST y pausas: markets para orientación, ticker solo si hace falta, `settle_sleep_ms: 0` por defecto.
- Config real en `projects/arbitraje/swapper.live.yaml` (`dry_run: false`).

## 0.4.2 (2025-10-12)

Swapper Alpha — balance settle pause
- Reintroducida una pequeña pausa entre hops para permitir que el saldo se asiente en el exchange y evitar cortes entre legs.
- `swapper.live.yaml`: `settle_sleep_ms` ajustado a 300 ms; `confirm_fill: false` se mantiene para velocidad.
- `swapper.yaml` (dry-run): `settle_sleep_ms` ajustado a 100 ms para simular más real, configurable.
- Sin cambios funcionales en la lógica de ejecución: path-first, fees neteados, balance real por hop.

# Changelog

All notable changes to this repository are documented here. Dates are in YYYY-MM-DD.

## v2.2.0-MEMO2 — 2025-10-20

Safety, mirror TTL re-emit and audit logs; monitor snapshot fixes

Highlights
- Swapper
  - Mirror last-leg protection: classify tiny last-hop fills as mirror_pending (neutral delta) using a dust threshold relative to input.
  - Minimums/precision: apply price_to_precision and validate min amount/notional for the mirror to reduce rejections.
  - Retry on "Insufficient position" (e.g., MEXC 30004) with slightly reduced amount to leave a pending limit order when feasible.
  - TTL-based re-emit: if the mirror order remains open and the mid moves favorably, cancel-and-replace at min(entry*(1-off), mid*(1-safety)) for buys (symmetric for sells). Bounded by protective price.
  - Auditability: explicit mirror_reemit log lines include old_limit → new_limit, mid, entry, order ids, attempt i/Max, and elapsed seconds.
- Monitor
  - Dynamic initial snapshot: when a new (exchange, asset) appears after the initial pass, set its "balance inicial" on the fly.
  - Dust gating (recommended): use min_value_anchor to avoid attempts under exchange minima; path to unified swapper log ensured.

Quality gates
- Build: PASS
- Lint/Typecheck: PASS
- Tests: manual dry-runs and small live validations; no unit suite changes

Upgrade notes
- Review `projects/arbitraje/swapper.live.yaml` for new keys:
  - mirror_reemit_ttl_sec, mirror_reemit_safety_bps, mirror_reemit_max
  - roundtrip_mirror_price_offset_bps now 8 bps by default
- Ensure the monitor uses the intended YAML via SCALPIN_CONFIG and consider min_value_anchor ≥ 5.0 USDT.

Tag sugerido: v2.2.0-MEMO2

## v1.1.0 — 2025-10-14

Minor release focusing on safety hardening for automated swap path generation and version alignment across the monorepo.

Highlights
- Blacklist support usage expanded: added manual `blacklist_pairs` entries in `swapper.yaml`, `swapper.live.yaml`, `arbitraje.yaml` y `arbitraje.prod.yaml` para excluir `okx: USDC/USDT` tras errores persistentes `sCode 51155` (compliance restriction) observados en `swapper.log`.
- Prevents constructing BF / swap cycles that would fail due to regulatory/compliance constraints on OKX USDC/USDT.
- Version bump root monorepo y paquete `arbitraje` a 1.1.0.

Why this matters
- Evita intentos repetitivos fallidos que generan ruido en logs y pérdidas de tiempo en ejecución automática.
- Centraliza la política de exclusión para futuras extensiones del cargador de blacklist.

Quality gates
- Build: PASS (Poetry metadata updated; no dependency changes).
- Lint/Typecheck: PASS (solo cambios en YAML/metadata, sin código Python nuevo).
- Tests: PASS (suite existente sin modificaciones; no paths funcionales afectados fuera del filtro de par restringido).

Upgrade notes
- No action required; rutas previas que usaban USDC/USDT en OKX simplemente dejarán de aparecer.
- Para revertir, eliminar la entrada en los YAML y borrar/editar `artifacts/arbitraje/logs/swapper_blacklist.json` si ya fue materializado.

Files changed
- `swapper.yaml`, `swapper.live.yaml`, `arbitraje.yaml`, `arbitraje.prod.yaml` (blacklist).
- `pyproject.toml` (root & arbitraje) version -> 1.1.0.
- `CHANGELOG.md` (esta sección) y nuevo `RELEASE_NOTES_v1.1.0.md`.

Tag sugerido: v1.1.0


## v1.0.0 — 2025-10-14 (GUILLERMO)

Major release consolidating the arbitraje scanner, live swapper, and quality gates, plus a one-line non-blocking autoswap trigger from the radar.

Highlights
- Radar (BF): non-blocking autoswap spawn on each qualifying opportunity using `swapper.live.yaml`.
- Stability: BF iteration flow fixes; cleaned history/snapshot logs; robust simulation summaries.
- Swapper: real-mode defaults in `swapper.live.yaml` (dry_run: false), minimal pauses (settle_sleep_ms: 300), and fast market flow.
- DX: VS Code tasks for install, scan, and quick BF runs; clearer docs and config precedence (CLI > YAML > defaults).

Quality gates
- Build: PASS (Poetry installs across projects)
- Lint/Typecheck: PASS (ruff permitted legacy ignores)
- Tests: PASS (unit tests where present; manual smoke runs for BF/Swapper)

## arbitraje v0.5.1 — 2025-10-14 (KILLER ALPHA)

BF logging and iteration reliability, plus simulation UX

- Snapshot logs restored and enriched: current_bf.txt now shows Simulation (estado actual) at the top and in the final summary; alias CURRENT_BF.txt mirrors it.
- History fixes: removed duplicate appends causing repeated "[BF] Iteración" headers; bf_history.txt now appends once per iteration and includes [SIM] picks.
- Multi-iteration loop fixed: removed a duplicated iteration path that could short-circuit or confuse iteration flow; now repeat N works cleanly with a simple sleep between iterations.
- Simulation summary correctness: iteration count reflects the actual last iteration reached (not the configured repeat).
- Small performance/robustness: currency micro-cache when rank-by-qvol is off; safer table rendering with fallbacks; headers/tables pre-drawn optionally for immediate structure.

Quality gates
- Build: PASS (Poetry install)
- Lint/Typecheck: PASS (ruff non-blocking legacy warnings allowed)
- Tests: PASS (project tests run; manual BF runs verified)

Artifacts
- Logs: artifacts/arbitraje/logs/current_bf.txt, CURRENT_BF.txt, bf_history.txt
- Outputs: arbitrage_bf_usdt_ccxt.csv, arbitrage_bf_simulation_summary_usdt_ccxt.csv, bf_sim_summary.{csv,md}, arbitrage_bf_usdt_persistence.csv

## arbitraje v0.4.0 — 2025-10-12 (swapper)

Minor release for the arbitraje project introducing the new Swapper module and performance-focused refinements for fast, isolated execution of spot round-trips.

Highlights
- New: Swapper OOP module (`src/arbitraje/swapper.py`) with its own YAML config, CLI, and VS Code tasks. Supports both test and real modes.
- Config: `projects/arbitraje/swapper.yaml` (defaults, dry-run on) and `projects/arbitraje/swapper.live.yaml` (live, dry-run off).
- Per-exchange minimums: YAML-driven `test_min_amounts` used in test mode; Binance minimum set to 10.0 USDT for USDT/USDC (practical NOTIONAL filter).
- Speed: Avoid heavy `load_markets`/`fetch_tickers`, use targeted `fetch_ticker`; optional fill confirmation; no sleeps by default.
- Cost-based market buys: Enabled for Bitget and Binance via ccxt options.
- Env: Auto-load `.env` from repo and project roots for API keys.

Docs & Tasks
- CLI entrypoints: `poetry run swapper` (alias `swaper`).
- VS Code tasks: "Arbitraje: Swapper (test USDT<->USDC)" and live config ready.
- Updated README with Swapper usage basics.

Quality gates
- Build: PASS (Poetry install).
- Lint/Typecheck: non-blocking ruff issues remain in legacy modules, no new errors in Swapper.
- Tests: PASS (existing tests run; Swapper manually validated with tiny real orders on OKX/Bitget/MEXC; Binance at 10 USDT).

## arbitraje v0.2.0 — 2025-10-11

Minor release for the arbitraje project focusing on YAML-driven configuration, safer balance handling, and cleanup.

Highlights
- Config: New `projects/arbitraje/arbitraje.yaml` with Spanish comments. Precedence is CLI > YAML > defaults. TRI and BF sections supported.
- Balance: When reading balances, if credentials are missing or wallet is inaccessible, balances are treated as 0 to avoid overstated PnL.
- Exchanges: Normalize common aliases (gateio→gate, okex→okx, coinbasepro→coinbase, huobipro→htx). Broadened credential env vars (OKX, KuCoin, Kraken, Gate.io, MEXC).
- TRI: Default `--config` now points to `projects/arbitraje/arbitraje.yaml`.
- SDKs: Added `bootstrap_sdks.py` to optionally clone official SDKs under `projects/arbitraje/sdk/*` using metadata in YAML.
- Docs: Updated `README.md` and `.env.example` for credential keys and optional SDK bootstrap.
- CI: New workflow `.github/workflows/arbitraje-ci.yml` to install, lint, test, and smoke-run help.
- Cleanup: Removed legacy CoinGecko/CoinPaprika demo (`coingecko_arbitrage_report.py` and `providers/coinpaprika.py`) and replaced VS Code task with a deprecation echo.

Quality gates
- Build: PASS (Poetry install).
- Lint/Typecheck: PASS (Ruff non-blocking in CI; no new issues introduced).
- Tests: PASS (unit tests in `projects/arbitraje/tests`).

## v0.3.0 — 2025-09-18

This release focuses on reliability for the Email Collector (Hotmail/Outlook IMAP), clearer logs, and a small quality-of-life update to the EasyBrokers tools.

Highlights
- Email Collector: Hotmail/Outlook IMAP OAuth device-code support with clearer error messages and safer folder selection (handles Junk/Spam variants more robustly).
- Configuration: Wider Hotmail folder include list; tightened spam heuristics; expanded Spanish transactional short allowlist; disabled domain subfolders so exports are organized by category only.
- Logging: Unified file logging for collectors and utilities under emails_out/logs/.
- Realstate tools: Structured logging to console and file; improved image downloader; declared dependencies (requests, openpyxl) and added lockfile.
- Developer experience: VS Code tasks to install deps and run both projects; docs updated.

Changes by area
- Email Collector
  - Add file logging to emails_out/logs/email_collector.log in addition to console output.
  - Harden OAuth device flow for Hotmail/Outlook (clearer errors, instructions, and token handling).
  - Improve folder selection (INBOX, Junk Email, Junk, Junk E-mail, Spam) with quoting and fuzzy matching fallbacks.
  - Config tweaks: keep Spanish validation, tune allowlist/keywords, and disable domain subfolders in output.
- Realstate
  - Add logging to file at realstate/logs/realstate_export.log.
  - Improve image downloader diagnostics and safety; sanitize filenames.
  - Add requests and openpyxl to pyproject; include poetry.lock for reproducible installs.
- Utilities & Docs
  - extract_domains.py and migrate_suspicious.py now log to emails_out/logs/.
  - Root README and project READMEs document tasks and .env quick-start.

Links
- Tag: https://github.com/CarlosCaPe/dataqbs_IA/tree/v0.3.0
