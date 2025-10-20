# Release Notes — v2.2.0-MEMO2

Date: 2025-10-20

This release focuses on safer round-trips with a mirrored last hop, better resilience on exchanges, and clearer audit logs. The monitor now initializes snapshots for assets that reappear mid-run.

What's new
- Mirror protections
  - Mirror last hop classified as `mirror_pending` on dust-level partials; delta is neutralized until resolution.
  - Exchange minimums respected: price_to_precision and min amount/notional checks before placing mirror orders.
  - One-shot retry on mirror order failures due to `Insufficient position` with a slightly reduced amount.
  - TTL-based cancel-and-replace (re-emit) for open mirror orders with a protective safety bound.
  - Rich audit logs for each re-emit attempt: `old_limit -> new_limit`, mid, entry, order ids, `attempt i/Max`, `elapsed_s`.
- Monitor improvements
  - Dynamic seeding of `balance inicial` for newly appearing assets.
  - Unified swapper log path via environment override; docs updated on where to find logs.

Configuration updates
- `projects/arbitraje/swapper.live.yaml`
  - `roundtrip_mirror_price_offset_bps: 8`
  - `roundtrip_mirror_amount_tolerance_bps: 5`
  - `mirror_reemit_ttl_sec: 120`
  - `mirror_reemit_safety_bps: 5`
  - `mirror_reemit_max: 2`
- `guillermo/scalpin.yaml`
  - Raise `min_value_anchor` to filter dust attempts (recommended ≥ 5 USDT).
  - `profit_action_threshold_pct: 0.10`.

Operational notes
- Ensure the monitor reads the intended YAML by setting `SCALPIN_CONFIG` to `guillermo/scalpin.yaml`.
- Logs:
  - Swapper: `C:\Users\Lenovo\Guillermo\guillermo\artifacts\arbitraje\logs\swapper.log`
  - Monitor CSVs: `C:\Users\Lenovo\Guillermo\guillermo\artifacts\scalpin\`

Quality gates
- Build: PASS
- Lint/Typecheck: PASS
- Tests: Dry-run validations, small live checks; no unit test changes in this release.

Next steps
- Optional: add monitor-side exchange-min gating before spawning swaps and cooldown while a mirror order is open.
