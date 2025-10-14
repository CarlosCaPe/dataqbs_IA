## Release v1.1.0 (2025-10-14)

Safety hardening for swap path generation via manual blacklist plus version alignment.

### Added
- Manual blacklist entry: `blacklist_pairs: okx: [USDC/USDT]` en:
  - `projects/arbitraje/swapper.yaml`
  - `projects/arbitraje/swapper.live.yaml`
  - `projects/arbitraje/arbitraje.yaml`
  - `projects/arbitraje/arbitraje.prod.yaml`

### Reason
Repeated swap failures with OKX error codes:
- `51155` (compliance restriction) on USDC/USDT
- Noise and wasted attempts when constructing BF cycles or executing test/live swaps involving that leg.

### Impact
- Cycles requiring USDC<->USDT on OKX will now be filtered out early.
- Reduces log noise and failed attempt overhead.

### Versions
- Root monorepo: 1.1.0
- Package `arbitraje`: 1.1.0

### Quality
- Build: PASS (no new deps)
- Lint: PASS (no Python changes)
- Tests: PASS (existing tests unaffected)

### Revert
Remove the blacklist entries from the YAMLs and delete/edit `artifacts/arbitraje/logs/swapper_blacklist.json` if present.

### Next ideas
- Auto-classify transient min-notional (51020) vs permanent compliance (51155) to avoid manual updates.
- Optional CLI to append to blacklist with reason and timestamp.
