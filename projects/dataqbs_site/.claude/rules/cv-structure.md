---
paths:
  - "src/data/cv.ts"
  - "src/data/cv_translations.ts"
  - "scripts/generate_cv_pdfs.py"
---

# CV Structure Rules

## Index Convention
All CV entries are numbered 0-11 (12 total). The index in `cv.ts` MUST match:
- `cv_translations.ts` ES section keys
- `cv_translations.ts` DE section keys
- `generate_cv_pdfs.py` ACH_ES array indices
- `generate_cv_pdfs.py` ACH_DE array indices

## Current Structure (as of 2026-03)
| Index | Company | Type | Period |
|-------|---------|------|--------|
| 0 | Hexaware Technologies | full-time | ended 2026-03 |
| 1 | dataqbs | freelance | 2017-06 → present |
| 2 | SVAM International | full-time | ended |
| 3 | Svitla Systems | contract | ended |
| 4 | Epikso Mexico | full-time | ended |
| 5 | Jabil (Data Technical Lead) | full-time | ended |
| 6 | 3Pillar Global | full-time | ended |
| 7 | HCL Technologies | full-time | ended |
| 8 | Jabil (IT Analyst) | full-time | ended |
| 9 | C&A SA de CV | full-time | ended |
| 10 | FIRMEPLUS | full-time | ended |
| 11 | Jabil Circuit de México | full-time | ended |

## Multi-Employment Rules
- **Full-time** roles CANNOT visually overlap with other full-times
- **Contracts** can overlap (they're under dataqbs umbrella)
- NewFire Global and FussionHit work are dataqbs clients, NOT separate entries

## Adding New Experience Entry
1. Add to `src/data/cv.ts` experiences array at correct index
2. If inserting (not appending), reindex ALL subsequent entries in:
   - `cv_translations.ts` ES section
   - `cv_translations.ts` DE section
   - `generate_cv_pdfs.py` ACH_ES
   - `generate_cv_pdfs.py` ACH_DE
3. Update `src/layouts/Layout.astro` JSON-LD `worksFor`
4. If company has notable tech, add trigger to `src/pages/api/chat.ts` QUERY_EXPANSION
5. **REGENERATE PDFs**: `python scripts/generate_cv_pdfs.py` ⚠️ CRITICAL
6. Build and deploy: `npm run build && npx wrangler pages deploy dist --project-name dataqbs-site`

## Removing Experience Entry
1. Remove from `cv.ts`
2. Remove translation from `cv_translations.ts` (ES and DE)
3. Remove achievements from `generate_cv_pdfs.py` (ACH_ES and ACH_DE)
4. Decrement all subsequent indices in translations and PDF generator
5. Update Layout.astro worksFor
6. Remove query expansion trigger if exists

## Client List in dataqbs Entry
The dataqbs entry (index 1) lists freelance clients:
- NewFire Global
- VCA Animal Hospitals
- C&A Mexico
- BCG, Moviro, Svitla, Quesos Navarro
- Contract work appears under dataqbs, NOT as separate CV entries
