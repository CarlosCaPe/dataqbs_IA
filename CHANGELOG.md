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
