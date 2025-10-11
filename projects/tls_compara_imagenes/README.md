# tls_compara_imagenes

Migrated from legacy `telus_compara_imagenes`.

## Console Scripts

Primary: `tls-compare-images`
Deprecated alias: `telus-compare` (prints warning then delegates)

## Artifacts
Artifacts stored under `artifacts/tls_compara_imagenes/` (logs, outputs, user_data).
A migration shim moves old `artifacts/telus_compara_imagenes` automatically if present.

## Status
This runner currently contains a simplified loop placeholder. For full parity with the original 1000+ line implementation, the remaining helper functions and decision logic can be ported incrementally.

## Next Steps
- Port remaining helper functions (image similarity, capture heuristics, CSV auditing).
- Add tests for metric functions.
- Remove deprecated alias in a future major bump.
