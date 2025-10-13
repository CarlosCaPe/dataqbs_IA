# v0.4.2 — Swapper Alpha (balance settle pause)

Date: 2025-10-12

This release restores a small, configurable pause between swap hops to give exchanges time to reflect balances before the next leg.

What changed
- Config: `projects/arbitraje/swapper.live.yaml` now sets `settle_sleep_ms: 300` (was 0).
- Config: `projects/arbitraje/swapper.yaml` (dry-run) now sets `settle_sleep_ms: 100` to mimic live behavior while keeping fast runs. Set to `0` for max speed.
- Code: `swapper.py` already respects `settle_sleep_ms`; no logic changes required.

Behavior is otherwise unchanged from 0.4.1:
- Path is authoritative; no anchor influences execution.
- First hop can be capped with `--amount`; rest of hops consume the real base balance.
- Fees are netted from exchange response; post-hop balance is re-read (with the optional pause) before proceeding.

Quality gates
- Build: PASS (Poetry install)
- Tests: PASS (existing tests)
- Lint: Known non-blocking issues outside swapper remain (BF/legacy modules); not part of this patch.

Notes
- You can adjust `settle_sleep_ms` per environment. For very fast exchanges or paper trading you may set `0`.
- Keep `confirm_fill: false` for speed unless you need very precise fee accounting per hop.
