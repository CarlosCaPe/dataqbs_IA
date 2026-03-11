# dataqbs_IA — Monorepo Context

> Universal constraints are in `~/.claude/CLAUDE.md`. This file covers repo-specific context only.

## Structure
Poetry monorepo at root `pyproject.toml`. Projects live under `projects/<name>/`.

| Project | Purpose |
|---------|---------|
| dataqbs_site | Portfolio + RAG chatbot (Astro/Svelte/CF Pages) |
| email_collector | IMAP ingest and categorization |
| arbitraje | Crypto arbitrage scanner (CCXT) |
| tls_compara_audios | Audio comparison tool (Playwright) |
| tls_compara_imagenes | Image comparison tool (Playwright) |
| real_estate | Real estate data tools |

## Quick Commands
```bash
poetry install            # Install all deps
poetry run pytest         # Run tests
poetry run ruff check .   # Lint
poetry run ruff format .  # Format
```

## Shared Config
- `config.yaml` — email, IMAP settings
- `scalpin.yaml` — market monitor settings

## Conventions
- Each project is self-contained under `projects/<name>/`
- VS Code tasks defined in `.vscode/tasks.json`
- Pre-commit hooks: gitleaks (blocks secrets)
