# SDK directory

This directory (`projects/arbitraje/sdk/`) stores optional SDK vendors used by the project.

Guidelines:

- Prefer using git submodules or the `bootstrap_sdks.py` helper script to fetch SDKs into `sdk/` instead of committing generated artifacts.
- If you need to vendor an SDK for offline builds, keep only the necessary code and avoid committing large `dist/`, `node_modules/`, or binary artifacts.
- Common tasks:
  - To update SDKs via submodules:

```bash
git submodule update --init --recursive
git submodule update --remote --merge
```

- To bootstrap using the helper (when available):

```bash
cd projects/arbitraje
poetry run python bootstrap_sdks.py
```

- If you must add an SDK snapshot, add a small `README.md` inside the SDK folder explaining the source and the commit/tag used.

Cleanup suggestions:

- Add `sdk/*/dist`, `sdk/*/node_modules`, and other generated folders to `.gitignore` to avoid accidental commits.
- Keep a short `sdk/INDEX.md` explaining which SDKs are installed and where they came from.
