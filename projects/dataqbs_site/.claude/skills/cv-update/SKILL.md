---
name: cv-update
description: Update CV with new experience entry, maintaining index alignment across all files
disable-model-invocation: true
---

# Update CV Entry

Add, modify, or remove an experience entry while maintaining index alignment.

## Files to Update
1. `src/data/cv.ts` — Main experience data
2. `src/data/cv_translations.ts` — ES and DE translations (keyed by index)
3. `scripts/generate_cv_pdfs.py` — ACH_ES and ACH_DE achievement arrays
4. `src/layouts/Layout.astro` — JSON-LD worksFor schema
5. `src/pages/api/chat.ts` — QUERY_EXPANSION triggers (if notable tech)

## Adding New Entry Steps

1. **Determine index position**
   - Current contract/job → Index 0 (shift everything down)
   - Past role → After current roles, before older positions

2. **Update cv.ts**
   ```typescript
   {
     company: 'Company Name',
     role: 'Role Title',
     period: { start: 'YYYY-MM', end: null }, // null = present
     type: 'contract' | 'full-time' | 'freelance',
     location: 'City, Country',
     clients: ['Client1', 'Client2'], // optional
   }
   ```

3. **Update cv_translations.ts**
   - Add ES translation at matching index
   - Add DE translation at matching index
   - If inserting, reindex ALL subsequent entries in both ES and DE

4. **Update generate_cv_pdfs.py**
   - Add achievements to ACH_ES at matching index
   - Add achievements to ACH_DE at matching index
   - If inserting, reindex ALL subsequent entries

5. **Update Layout.astro**
   - Add to JSON-LD worksFor array:
   ```javascript
   { '@type': 'Organization', name: 'Company Name' }
   ```

6. **Update chat.ts (if needed)**
   - Add QUERY_EXPANSION trigger if company has notable tech stack

7. **REGENERATE PDFs** ⚠️ CRITICAL
   ```bash
   python scripts/generate_cv_pdfs.py
   ```
   This updates Profile.pdf, Profile_ES.pdf, Profile_DE.pdf in public/

8. **Build and Deploy**
   ```bash
   npm run build
   npx wrangler pages deploy dist --project-name dataqbs-site
   ```

## Removing Entry Steps

1. Remove from cv.ts
2. Remove from cv_translations.ts (ES and DE)
3. Remove from generate_cv_pdfs.py (ACH_ES and ACH_DE)
4. Decrement ALL subsequent indices
5. Remove from Layout.astro worksFor
6. Remove from chat.ts QUERY_EXPANSION (if exists)

## Multi-Employment Rules
- Full-time roles CANNOT overlap with other full-times
- Contracts CAN overlap (under dataqbs umbrella)
- FussionHit = VCA project under dataqbs, NOT separate entry

## Index Verification
After any change, verify indices match across all files:
- cv.ts experiences[N]
- cv_translations.ts es[N] / de[N]
- generate_cv_pdfs.py ACH_ES[N] / ACH_DE[N]
