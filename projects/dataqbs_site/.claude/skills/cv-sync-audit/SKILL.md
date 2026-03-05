---
name: cv-sync-audit
description: Verify all CV-related files are synchronized (indices, companies, dates, achievements)
disable-model-invocation: true
---

# CV Synchronization Audit

Run this audit AFTER any CV change to catch mismatches before deployment.

## Files to Cross-Reference
1. `src/data/cv.ts` — Source of truth
2. `src/data/cv_translations.ts` — ES and DE translations
3. `scripts/generate_cv_pdfs.py` — ACH_ES and ACH_DE arrays
4. `.claude/rules/cv-structure.md` — Documentation table
5. `src/pages/api/chat.ts` — QUERY_EXPANSION triggers

## Automated Audit (Preferred)
```bash
python scripts/validate_cv_sync.py
```

## Manual Audit Checklist

### 1. Count Entries
```bash
# cv.ts — count company: lines
grep -c "company:" src/data/cv.ts

# cv_translations.ts — count ES entries (lines with "// N —")
grep -c "// [0-9]* —" src/data/cv_translations.ts | head -1

# generate_cv_pdfs.py — count ACH_ES entries
grep -c "# [0-9]*:" scripts/generate_cv_pdfs.py | head -1
```
All three should return the same number (currently 12).

### 2. Verify Index Alignment
For each index 0-11, confirm:
- [ ] cv.ts experiences[N].company matches
- [ ] cv_translations.ts es[N] comment matches
- [ ] cv_translations.ts de[N] comment matches
- [ ] generate_cv_pdfs.py ACH_ES[N] comment matches
- [ ] generate_cv_pdfs.py ACH_DE[N] comment matches

### 3. Verify Dates
Check cv.ts period.start and period.end against:
- [ ] cv-structure.md table (documentation)
- [ ] PDF output (download and verify)

### 4. Verify Employment Types
Cross-reference cv.ts `type` field:
- `full-time` → Cannot overlap with other full-times
- `contract` → Can overlap (under dataqbs umbrella)
- `freelance` → dataqbs only, runs parallel to everything

### 5. Verify Client List
dataqbs (index 1) achievements should list:
- [ ] NewFire Global
- [ ] VCA Animal Hospitals
- [ ] C&A México
- [ ] BCG, Moviro, Svitla, Quesos Navarro

No client should have a separate CV entry.

### 6. Verify chat.ts Triggers
Companies with notable tech should have QUERY_EXPANSION entries:
- [ ] hexaware → mining, Snowflake, ADX, IROC
- [ ] dataqbs → freelance, clients, MEMO-GRID
- [ ] newfire → dataqbs, client, freelance

## Common Mismatches

| Symptom | Likely Cause |
|---------|--------------|
| PDF shows wrong company | ACH_ES/ACH_DE index mismatch |
| ES/DE translation missing | cv_translations.ts not updated |
| Chatbot gives wrong info | chat.ts QUERY_EXPANSION stale |
| Timeline overlap error | Full-time dates conflict |
| Wrong date in production | cv.ts updated but PDFs not regenerated |

## After Fixing Mismatches
1. Run `python scripts/validate_cv_sync.py`
2. Regenerate PDFs: `python scripts/generate_cv_pdfs.py`
3. Build: `npm run build`
4. Deploy: `npx wrangler pages deploy dist --project-name dataqbs-site`
5. Verify in production: https://www.dataqbs.com
