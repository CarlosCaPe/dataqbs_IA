# dataqbs_IA — AI Agent Instructions

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
- **CORS**: Locked to `https://www.dataqbs.com` — never set to `*`.
- **WAF**: Cloudflare dashboard rate limiting rule: 15 req/10s on `/api/*`.
- **Headers**: HSTS, X-Frame-Options DENY, nosniff, Referrer-Policy strict — set in `public/_headers`.

### When Adding New API Endpoints
1. Add Turnstile validation (check `TURNSTILE_SECRET_KEY` env var)
2. Set CORS to production domain only
3. Add rate limiting (in-memory as fallback, WAF rule in dashboard)
4. Sanitize all user inputs before use in HTML/email
5. Never log or expose API keys in responses

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
