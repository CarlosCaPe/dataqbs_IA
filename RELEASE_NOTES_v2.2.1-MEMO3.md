# Release Notes — v2.2.1-MEMO3

Date: 2025-10-20

This release adds configurable auto sizing, symbol-level overrides, and clearer diagnostics when attempting swaps with zero balance. It complements the prior mirror TTL/relaxation features.

What's new
- Auto sizing
  - New `sizing` section in `projects/arbitraje/swapper.live.yaml` (mode: auto|manual).
  - Computes a USD cap for the first hop when `plan.amount=0`, converts to source units using top-of-book vs USDT/USDC, clamps `[min_usd, max_usd]`.
  - Per-exchange/symbol `overrides` (e.g., `binance -> ZEC/USDT`) to tune min/max and other knobs.
- Mirror and logging
  - `mirror_placed` audit log: symbol, side, limit, amount, entry, tolerance, sizing mode, and first_cap_units.
  - Start/result log suffix with sizing summary; per-hop `no_funds` info when free balance is zero to clarify failures like those seen on Binance.
  - Existing mirror re-emit logs continue to include `delta_bps` and `relax_used_bps`.

Config updates
- `projects/arbitraje/swapper.live.yaml`
  - Added `sizing:` block with safe defaults and an example override for `binance: ZEC/USDT`.

Quality gates
- Build: PASS
- Lint/Typecheck: PASS
- Tests: Manual smoke (dry-run/live). No unit test changes.

Next steps
- Optional: extend auto sizing to laddered mirrors using `ladder_levels` and `ladder_step_bps`.
- Optional: Add monitor-side gating for exchange minimums before spawning swaps.
