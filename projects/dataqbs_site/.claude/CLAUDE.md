# dataqbs_site — AI Agent Instructions

## ⚠️ Keep Instructions In Sync
This file and `../../.github/copilot-instructions.md` must stay synchronized.
When updating CV workflows, security rules, or deployment steps here, also update the Copilot instructions.
Both AI assistants should give the same guidance for the same project.

## Project Overview
Portfolio website + RAG chatbot for dataqbs.com. Astro 4.16 + Svelte 4 + Tailwind 3.4, deployed on Cloudflare Pages (hybrid SSR).

## Quick Commands
```bash
npm run dev              # Local dev server (port 4321)
npx astro build          # Production build
npx wrangler pages deploy dist --project-name dataqbs-site
```

## Key Files
| File | Purpose |
|------|---------|
| `src/data/cv.ts` | Experience entries (13 items, indexed 0-12) |
| `src/data/cv_translations.ts` | ES/DE translations keyed by index |
| `scripts/generate_cv_pdfs.py` | PDF generation (ACH_ES, ACH_DE by index) |
| `src/pages/api/chat.ts` | RAG chatbot endpoint with query expansion |
| `src/pages/api/contact.ts` | Contact form handler (5 security layers) |
| `src/components/ContactSection.svelte` | Form UI with honeypot |
| `src/layouts/Layout.astro` | JSON-LD schema, CSP nonce |

## Architecture
- **SSR**: Cloudflare Pages adapter with D1/KV bindings
- **Chatbot**: Groq LLM + vector embeddings from `knowledge.json` (KV)
- **Security**: Turnstile → Honeypot → Speed check → Origin → Rate limit
- **Build**: `public/_headers` sets HSTS, CSP, X-Frame-Options

## CV Index Convention
All CV-related files MUST share the same index order:
- Index 0: NewFire Global (current contract)
- Index 1: Hexaware (ended full-time)
- Index 2: dataqbs (ongoing freelance)
- Indices 3-12: Past roles in reverse chronological order

When adding/removing entries:
1. Update `cv.ts` first
2. Reindex `cv_translations.ts` (ES and DE sections)
3. Reindex `generate_cv_pdfs.py` (ACH_ES and ACH_DE arrays)
4. Update `Layout.astro` JSON-LD worksFor
5. Update `chat.ts` query expansion triggers
6. **REGENERATE PDFs**: `python scripts/generate_cv_pdfs.py` ⚠️

Missing step 6 = outdated PDFs in production!

## Security Rules (Mandatory)
See @.claude/rules/security.md for full security checklist.

## Additional Rules
- @.claude/rules/cv-structure.md
- @.claude/rules/deployment.md
