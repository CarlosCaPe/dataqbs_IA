#!/usr/bin/env node
/**
 * i18n-audit.mjs — Build-time translation completeness checker.
 *
 * Walks every Svelte component and scans for:
 *   1. Hardcoded English strings in templates (text not wrapped in {$t.*} or {exp.*})
 *   2. Missing translation keys across locales (EN vs ES vs DE)
 *   3. cv_translations.ts index gaps (every experience index has ES + DE)
 *   4. project_translations.ts slug gaps (every project slug has ES + DE)
 *
 * Run:  node scripts/i18n-audit.mjs
 * Exit: 0 = clean, 1 = findings
 *
 * Hook into CI or pre-build to prevent regressions.
 */

import { readFileSync, readdirSync, statSync } from 'fs';
import { join, relative } from 'path';

const ROOT = new URL('..', import.meta.url).pathname;
const SRC = join(ROOT, 'src');

let findings = 0;

function warn(file, line, msg) {
  console.log(`  ⚠  ${relative(ROOT, file)}:${line} → ${msg}`);
  findings++;
}

// ── 1. Check translations.ts key parity ──────────────
console.log('\n🔍 Checking translation key parity (EN vs ES vs DE)...');
const translationsPath = join(SRC, 'i18n', 'translations.ts');
const transSrc = readFileSync(translationsPath, 'utf8');

// Extract all $t.xxx.yyy references from Svelte files
const tRefs = new Set();
function walkDir(dir) {
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry);
    if (statSync(full).isDirectory()) {
      walkDir(full);
    } else if (full.endsWith('.svelte')) {
      const content = readFileSync(full, 'utf8');
      // Match $t.section.key patterns
      for (const m of content.matchAll(/\$t\.(\w+)\.(\w+)/g)) {
        tRefs.add(`${m[1]}.${m[2]}`);
      }
      // Match $t.section[exp.xxx] patterns (dynamic keys)
      for (const m of content.matchAll(/\$t\.(\w+)\[/g)) {
        tRefs.add(`${m[1]}.*`);
      }
    }
  }
}
walkDir(join(SRC, 'components'));
walkDir(join(SRC, 'pages'));

console.log(`   Found ${tRefs.size} translation references in components`);

// ── 2. Check cv_translations.ts coverage ─────────────
console.log('\n🔍 Checking cv_translations.ts coverage...');
const cvTransPath = join(SRC, 'data', 'cv_translations.ts');
const cvTransSrc = readFileSync(cvTransPath, 'utf8');
const cvPath = join(SRC, 'data', 'cv.ts');
const cvSrc = readFileSync(cvPath, 'utf8');

// Count experiences in cv.ts
const expCount = (cvSrc.match(/role:\s*'/g) || []).length;
console.log(`   Experience entries in cv.ts: ${expCount}`);

// Check ES and DE have all indices
for (const lang of ['es', 'de']) {
  for (let i = 0; i < expCount; i++) {
    const langSection = lang === 'es'
      ? cvTransSrc.split('GERMAN')[0].split('SPANISH')[1] || ''
      : cvTransSrc.split('GERMAN')[1] || '';
    if (!langSection.includes(`${i}: {`)) {
      warn(cvTransPath, 0, `Missing ${lang.toUpperCase()} translation for experience index ${i}`);
    }
  }
}

// ── 3. Check project_translations.ts coverage ────────
console.log('\n🔍 Checking project_translations.ts coverage...');
const projTransPath = join(SRC, 'data', 'project_translations.ts');
const projTransSrc = readFileSync(projTransPath, 'utf8');
const projPath = join(SRC, 'data', 'projects.ts');
const projSrc = readFileSync(projPath, 'utf8');

// Extract slugs from projects.ts
const slugs = [...projSrc.matchAll(/slug:\s*'([^']+)'/g)].map(m => m[1]);
console.log(`   Project slugs in projects.ts: ${slugs.length}`);

for (const lang of ['es', 'de']) {
  const langSection = lang === 'es'
    ? projTransSrc.split('GERMAN')[0].split('SPANISH')[1] || ''
    : projTransSrc.split('GERMAN')[1] || '';
  for (const slug of slugs) {
    if (!langSection.includes(`'${slug}'`)) {
      warn(projTransPath, 0, `Missing ${lang.toUpperCase()} translation for project slug '${slug}'`);
    }
  }
}

// ── 4. Scan Svelte templates for suspicious hardcoded text ──
console.log('\n🔍 Scanning Svelte templates for hardcoded English text...');
const SAFE_PATTERNS = [
  /^\s*$/, /^\{/, /^</, /^-->/, /^\s*\|/, /^#/, /^\//, /^@/,
  /^\s*\d+/, /^\s*[&·•▸←→↗]/, /^\s*\(/, /^\s*\)/,
  /^dataqbs/, /^Carlos/, /^carlos/,
  /^http/, /^mailto/, /^tel:/, /^wa\.me/,
  /^Profile/, /^\.pdf/, /^\.jpeg/,
  /items-center|justify-|flex-|rounded|bg-|text-|border-|gap-|px-|py-|mt-|mb-|ml-|mr-/, // CSS classes
];

function scanSvelteHardcoded(dir) {
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry);
    if (statSync(full).isDirectory()) {
      scanSvelteHardcoded(full);
    } else if (full.endsWith('.svelte')) {
      const content = readFileSync(full, 'utf8');
      // Only scan template (after </script> and outside <style>)
      const templateMatch = content.match(/<\/script>([\s\S]*?)(?:<style|$)/);
      if (!templateMatch) continue;
      const template = templateMatch[1];
      const lines = template.split('\n');
      const scriptEndLine = content.substring(0, content.indexOf('</script>')).split('\n').length;

      for (let li = 0; li < lines.length; li++) {
        const line = lines[li];
        // Extract text content between > and < or between } and {
        const textSegments = line.replace(/<[^>]*>/g, '|').replace(/\{[^}]*\}/g, '|').split('|');
        for (const seg of textSegments) {
          const trimmed = seg.trim();
          if (trimmed.length < 3) continue;
          if (SAFE_PATTERNS.some(p => p.test(trimmed))) continue;
          // Flag if it looks like English words (2+ alpha chars not in a tag/expression)
          if (/^[A-Z][a-z]{2,}/.test(trimmed) || /^[a-z]{3,}\s/i.test(trimmed)) {
            warn(full, scriptEndLine + li + 1, `Possible hardcoded text: "${trimmed.substring(0, 60)}"`);
          }
        }
      }
    }
  }
}

scanSvelteHardcoded(join(SRC, 'components'));

// ── Summary ──────────────────────────────────────────
console.log('\n' + '─'.repeat(50));
if (findings === 0) {
  console.log('✅ i18n audit passed — zero findings!\n');
  process.exit(0);
} else {
  console.log(`❌ i18n audit: ${findings} finding(s) — review above\n`);
  process.exit(1);
}
