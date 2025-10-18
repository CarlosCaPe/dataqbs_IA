Worker diagnostics

- `diag_paths.jsonl`: canonical JSON-lines file written by worker processes. Each line contains:
  - ts: unix timestamp
  - msg: diagnostic message
  - attempted: list of attempted paths with {path, ok, err}
  - wrote: boolean if any write succeeded

- `diagnostics.log`: compact timestamped lines for local debugging (duplicated into `projects/arbitraje/src/artifacts/arbitraje/diagnostics.log`)

Housekeeping

- Use `diag_housekeeping.py` to rotate or truncate `diag_paths.jsonl` when it grows large.

Examples

```powershell
Set-Location projects\arbitraje
# rotate
poetry run python tools\diag_housekeeping.py rotate --path ..\..\artifacts\arbitraje --keep 100
# truncate
poetry run python tools\diag_housekeeping.py truncate --path ..\..\artifacts\arbitraje --max-lines 5000
```
