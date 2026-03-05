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
| 0 | Hexaware Technologies | full-time | 2025-03 → 2026-03 |
| 1 | dataqbs | freelance | 2011-01 → present |
| 2 | SVAM International Inc. | contract | 2022-11 → 2024-09 |
| 3 | Svitla Systems, Inc. | contract | 2021-05 → 2023-10 |
| 4 | Epikso Mexico | contract | 2022-01 → 2023-01 |
| 5 | Jabil (Data Technical Lead) | full-time | 2018-01 → 2022-03 |
| 6 | 3Pillar Global | full-time | 2016-06 → 2018-01 |
| 7 | HCL Technologies | full-time | 2014-08 → 2016-06 |
| 8 | Jabil (Database Analyst II) | full-time | 2011-08 → 2014-08 |
| 9 | C&A México | full-time | 2005-09 → 2011-08 |
| 10 | FIRMEPLUS | full-time | 2004-04 → 2005-05 |
| 11 | Jabil Circuit de México | full-time | 2003-08 → 2004-03 |

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
