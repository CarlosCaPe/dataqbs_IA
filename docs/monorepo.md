# Monorepo Structure

This document describes the layout and conventions of the `dataqbs_IA` monorepo.

## Goals
- Isolate independent Python projects under `projects/`.
- Keep generated artifacts out of version control under `artifacts/` (ignored) while preserving directory structure with `.gitkeep`.
- Provide a single top-level tooling environment (ruff, pytest, pre-commit) without forcing dependency coupling between sub‑projects.
- Encourage a consistent `src/` layout for import clarity and packaging readiness.

## Directories
- `projects/<name>/pyproject.toml` – project‑specific dependencies & scripts.
- `projects/<name>/src/<package>/` – Python package code.
- `projects/<name>/tests/` – test modules (pytest).
- `rules/` – domain rule sets (e.g., email classification heuristics).
- `tools/` – maintenance & one‑off operational scripts (grouped by domain).
- `artifacts/` – runtime outputs (emails, runs, logs, exports) NOT committed.
- `docs/` – architecture and domain guidance.

## Adding a New Project
1. `mkdir -p projects/new_project/src/new_project`.
2. Create `pyproject.toml` with dependencies.
3. Add tests in `projects/new_project/tests`.
4. Run `poetry install` inside the project for isolated env OR rely on a global environment manager.
5. Add any large outputs to `artifacts/new_project/`.

## Testing
Run only evaluator tests (fast):
```
poetry run pytest
```
Add additional testpaths by extending `[tool.pytest.ini_options].testpaths` in root `pyproject.toml` or project-local configurations.

## Linting & Formatting
```
poetry run ruff check .
poetry run ruff format .
```
Automated on commit via pre‑commit hooks (install with `pre-commit install`).

## Import Paths
Root pytest config injects each `src/` directory into `PYTHONPATH` for test discovery. Inside a project, prefer relative imports within the package; avoid cross‑project imports unless explicitly intended.

## Versioning & Changelog
Each project may maintain its own version in its `pyproject.toml`. High-level repo changes reflected in `CHANGELOG.md`.

## Future Enhancements
- Centralized coverage reporting.
- MyPy strict optional typing.
- Build matrix CI (per project) using GitHub Actions.
- Artifact retention policy (automatic cleanup scripts under `tools/`).
