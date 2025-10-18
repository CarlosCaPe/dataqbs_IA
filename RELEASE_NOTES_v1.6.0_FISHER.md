# v1.6.0 — FISHER

Date: 2025-10-18

This release focuses on making the Bellman-Ford (BF) loop reliable, observable, and documented. It aligns README and flow docs with actual runtime behavior and clarifies where simulation outputs live for downstream training.

What changed
- Fixed the BF iteration flow so every iteration reaches CSV persistence; moved/guarded sleeps and removed premature continues.
- Added rich [TIMING] instrumentation per iteration and per exchange worker for: setup, load_markets, adjacency build, currency selection, fetch_tickers, and delegation to techniques.
- Wrote snapshot headers early (Progress/Headers) in `current_bf.txt` to make stalls visible while work proceeds.
- Ensured `[SIM]` picks are recorded in `current_bf.txt` and appended to `bf_history.txt`, plus dedicated CSVs for analysis/training.
- Confirmed and documented output files: `arbitrage_bf_current_<quote>_ccxt.csv`, `arbitrage_bf_<quote>_ccxt.csv`, `arbitrage_bf_simulation_<quote>_ccxt.csv`, `arbitrage_bf_simulation_summary_<quote>_ccxt.csv`, `arbitrage_bf_<quote>_persistence.csv`, `bf_sim_summary.{csv,md}`.

Docs
- Updated `projects/arbitraje/README.md` and `projects/arbitraje/docs/flujo_arbitraje.md` to match the current pipeline and artifacts.

Versions
- Root monorepo: 1.6.0
- `arbitraje` package: 1.6.0 (engine label 3.2)

Quality gates
- Build: PASS
- Lint/Typecheck: PASS
- Tests: PASS (smoke run BF 1x)

Tag: V1.6.0-FISHER
