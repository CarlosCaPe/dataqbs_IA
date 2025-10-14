# dataqbs_IA — arbitraje v0.5.1 (KILLER ALPHA)

Date: 2025-10-14
Tag: v0.5.1

## Highlights

- BF snapshot logs restored and enriched
  - `current_bf.txt` shows "Simulación (estado actual)" at the top and in the final summary.
  - `CURRENT_BF.txt` mirrors the snapshot.
- History reliability
  - Removed duplicate appends; `bf_history.txt` now appends once per iteration and includes `[SIM]` picks.
- Multi-iteration loop fixed
  - Removed a duplicated inner iteration flow that could short-circuit runs; clean `repeat N` with a simple sleep.
- Simulation summary correctness
  - Iteration count reflects the actual iteration reached, not just the configured repeat.
- Small perf/UX
  - Currency micro-cache when rank-by-qvol is OFF; safer table rendering fallbacks; optional pre-drawn sections for immediate structure.

## Artifacts

- Logs:
  - `artifacts/arbitraje/logs/current_bf.txt`
  - `artifacts/arbitraje/logs/CURRENT_BF.txt`
  - `artifacts/arbitraje/logs/bf_history.txt`
- Outputs:
  - `artifacts/arbitraje/outputs/arbitrage_bf_usdt_ccxt.csv`
  - `artifacts/arbitraje/outputs/arbitrage_bf_simulation_summary_usdt_ccxt.csv`
  - `artifacts/arbitraje/outputs/bf_sim_summary.csv`
  - `artifacts/arbitraje/outputs/bf_sim_summary.md`
  - `artifacts/arbitraje/outputs/arbitrage_bf_usdt_persistence.csv`

## Quality Gates

- Build: PASS (Poetry install)
- Lint/Typecheck: PASS (ruff non-blocking legacy warnings allowed)
- Tests: PASS (project tests run; manual BF runs verified)
