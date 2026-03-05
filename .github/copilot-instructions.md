# dataqbs_IA — AI Agent Instructions

## ⚠️ Keep Instructions In Sync
This file (`copilot-instructions.md`) and `projects/dataqbs_site/.claude/CLAUDE.md` (+ rules/) must stay synchronized.
When updating CV workflows, security rules, or deployment steps here, also update the Claude Code files.
Both AI assistants should give the same guidance for the same project.

## Repository Structure

- **Monorepo** managed by Poetry at the root `pyproject.toml`
- Projects live under `projects/<name>/` — each is a self-contained tool/service
- Shared config: `config.yaml` (email, IMAP), `scalpin.yaml` (market monitor)

### Active Projects

| Project | Path | Purpose |
|---------|------|---------|
| dataqbs_site | `projects/dataqbs_site/` | Portfolio + RAG chatbot (Astro/Svelte/CF Pages) |
| email_collector | `projects/email_collector/` | IMAP ingest and categorization |
| arbitraje | `projects/arbitraje/` | Crypto arbitrage scanner (CCXT) |
| tls_compara_audios | `projects/tls_compara_audios/` | Audio comparison tool (Playwright) |
| tls_compara_imagenes | `projects/tls_compara_imagenes/` | Image comparison tool (Playwright) |
| real_estate | `projects/real_estate/` | Real estate data tools |

## Security Rules (MANDATORY)

These rules apply to ALL projects in this repo, especially `dataqbs_site`:

### Never Commit Secrets
- `.dev.vars`, `.env`, `.env.local`, `.env.production` must be in `.gitignore`
- API keys go in Cloudflare Pages secrets (via `wrangler pages secret put`)
- Pre-commit hook `gitleaks` blocks secrets — do NOT bypass it

### dataqbs_site Security Stack
- **Turnstile**: Required on every public endpoint (`/api/chat`, `/api/contact`). Always validate server-side.
- **CSP Nonce**: `src/middleware.ts` generates per-request nonce for `script-src`. Never revert to `unsafe-inline`.
- **DOMPurify**: `src/lib/markdown.ts` sanitizes all `{@html}` output. Never bypass the allowlist.
- **htmlEncode**: `src/pages/api/contact.ts` encodes all user inputs in email HTML. Never interpolate raw user data.
- **System Prompt**: `src/pages/api/chat.ts` must never contain PII (phone numbers, exact rates, pricing formulas).
- **Knowledge Store**: `knowledge.json` is stored in Cloudflare KV (`KNOWLEDGE_STORE` binding), NOT in `public/`. Route `src/pages/knowledge.json.ts` blocks any public access.
- **CORS**: Locked to `https://www.dataqbs.com` — never set to `*`.
- **WAF**: Cloudflare dashboard rate limiting rule: 15 req/10s on `/api/*`.
- **Headers**: HSTS, X-Frame-Options DENY, nosniff, Referrer-Policy strict — set in `public/_headers`.

### Five-Layer Defense (Contact Form)
1. **Turnstile** — Server-side validation via `TURNSTILE_SECRET_KEY`
2. **Honeypot** — Hidden `website` field; reject silently if filled
3. **Speed check** — `_loadedAt` timestamp; reject if < 3 seconds
4. **Origin header** — Must match `https://www.dataqbs.com`
5. **Rate limiting** — 3 req/min per IP + WAF rule (15 req/10s)

### When Adding New API Endpoints
1. Add Turnstile validation (check `TURNSTILE_SECRET_KEY` env var)
2. Set CORS to production domain only
3. Add rate limiting (in-memory as fallback, WAF rule in dashboard)
4. Sanitize all user inputs before use in HTML/email
5. Never log or expose API keys in responses

## CV Structure Rules (dataqbs_site)

### Index Convention
All CV entries indexed 0-11 (12 total) MUST match across these files:
- `src/data/cv.ts` — Main experience data
- `src/data/cv_translations.ts` — ES and DE translations (keyed by index)
- `scripts/generate_cv_pdfs.py` — ACH_ES and ACH_DE arrays
- `src/layouts/Layout.astro` — JSON-LD worksFor
- `src/pages/api/chat.ts` — QUERY_EXPANSION triggers

### Current Structure (2026-03)
| Index | Company | Type |
|-------|---------|------|
| 0 | Hexaware Technologies | full-time (ended) |
| 1 | dataqbs | freelance (ongoing) |
| 2-11 | Past roles | various |

### Multi-Employment Rules
- **Full-time** roles CANNOT visually overlap
- **Contracts** can overlap (under dataqbs umbrella)
- NewFire Global and FussionHit = dataqbs clients, NOT separate entries

### CV Update Workflow ⚠️ CRITICAL
When adding/modifying CV entries, follow this order:
1. Update `cv.ts`
2. Reindex `cv_translations.ts` (ES and DE)
3. Reindex `generate_cv_pdfs.py` (ACH_ES and ACH_DE)
4. Update `Layout.astro` JSON-LD worksFor
5. Update `chat.ts` QUERY_EXPANSION (if needed)
6. **REGENERATE PDFs**: `python scripts/generate_cv_pdfs.py`
7. Build: `npm run build`
8. Deploy: `npx wrangler pages deploy dist --project-name dataqbs-site`

Missing step 6 will cause PDF downloads to show outdated CV data!

## Developer Workflows

### dataqbs_site
```bash
cd projects/dataqbs_site
npm install
npm run dev                    # Local dev server
npx astro build                # Production build
npx wrangler pages deploy dist --project-name dataqbs-site  # Deploy
```

### Monorepo (Poetry)
```bash
poetry install                 # Install all deps
poetry run pytest              # Run tests
poetry run ruff check .        # Lint
poetry run ruff format .       # Format
```

### Pre-commit
```bash
pre-commit install             # One-time setup
pre-commit run --all-files     # Manual scan
```

## Conventions
- Config-first: behavior defined in YAML files, wired in code
- Use VS Code tasks (`.vscode/tasks.json`) for common operations
- All projects should have a README.md explaining setup and run commands
- Keep logs in `logs/` directories, never commit log files
