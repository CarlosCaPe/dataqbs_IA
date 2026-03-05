#!/usr/bin/env python3
"""
validate_cv_sync.py — Validate that all CV files are synchronized.

Checks consistency across:
- src/data/cv.ts (source of truth)
- src/data/cv_translations.ts (ES and DE translations)
- scripts/generate_cv_pdfs.py (ACH_ES and ACH_DE arrays)

Usage:
    python scripts/validate_cv_sync.py

Exit codes:
    0 — All files synchronized
    1 — Mismatches found
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from collections import defaultdict

# ── Paths ──
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
CV_TS = PROJECT_DIR / "src" / "data" / "cv.ts"
CV_TRANS_TS = PROJECT_DIR / "src" / "data" / "cv_translations.ts"
GEN_PDF_PY = SCRIPT_DIR / "generate_cv_pdfs.py"

# Expected number of experience entries
EXPECTED_COUNT = 12


def extract_companies_from_cv_ts(content: str) -> list[tuple[str, str, str]]:
    """Extract company names, roles, and periods from cv.ts experience array."""
    companies = []
    
    # Find the experience array
    exp_match = re.search(r'export const experience:\s*Experience\[\]\s*=\s*\[', content)
    if not exp_match:
        return companies
    
    # Extract each company block
    # Look for company: 'Company Name' patterns
    company_pattern = re.compile(
        r"company:\s*['\"]([^'\"]+)['\"].*?"
        r"role:\s*['\"]([^'\"]+)['\"].*?"
        r"period:\s*\{\s*start:\s*['\"]([^'\"]+)['\"]",
        re.DOTALL
    )
    
    for match in company_pattern.finditer(content):
        companies.append((match.group(1), match.group(2), match.group(3)))
    
    return companies


def extract_translation_indices(content: str, lang: str) -> set[int]:
    """Extract index keys from cv_translations.ts for a given language."""
    indices = set()
    
    # Find the language block (e.g., const es: Record<number, ...> = {)
    lang_pattern = re.compile(
        rf"const {lang}:\s*Record<number,\s*ExperienceTranslation>\s*=\s*\{{",
        re.IGNORECASE
    )
    
    match = lang_pattern.search(content)
    if not match:
        return indices
    
    # From this point, find all // N — patterns or just N: { patterns
    index_pattern = re.compile(r'//\s*(\d+)\s*[—-]|^\s*(\d+):\s*\{', re.MULTILINE)
    
    for m in index_pattern.finditer(content[match.end():]):
        idx_str = m.group(1) or m.group(2)
        if idx_str:
            indices.add(int(idx_str))
    
    return indices


def count_ach_entries(content: str, array_name: str) -> int:
    """Count entries in ACH_ES or ACH_DE array by counting comment markers."""
    # Find the array
    pattern = re.compile(rf"{array_name}\s*=\s*\[", re.IGNORECASE)
    match = pattern.search(content)
    if not match:
        return 0
    
    # Find the closing bracket by tracking nesting
    start = match.end()
    depth = 1
    pos = start
    while pos < len(content) and depth > 0:
        if content[pos] == '[':
            depth += 1
        elif content[pos] == ']':
            depth -= 1
        pos += 1
    
    array_content = content[start:pos-1]
    
    # Count # N: comment patterns
    comment_pattern = re.compile(r'#\s*\d+:')
    return len(comment_pattern.findall(array_content))


def extract_ach_company_comments(content: str, array_name: str) -> list[str]:
    """Extract company names from ACH array comments like '# 0: Hexaware Technologies'."""
    companies = []
    
    pattern = re.compile(rf"{array_name}\s*=\s*\[", re.IGNORECASE)
    match = pattern.search(content)
    if not match:
        return companies
    
    # Find the array content
    start = match.end()
    depth = 1
    pos = start
    while pos < len(content) and depth > 0:
        if content[pos] == '[':
            depth += 1
        elif content[pos] == ']':
            depth -= 1
        pos += 1
    
    array_content = content[start:pos-1]
    
    # Extract company names from comments
    comment_pattern = re.compile(r'#\s*(\d+):\s*([^\(\n]+)')
    for m in comment_pattern.finditer(array_content):
        companies.append((int(m.group(1)), m.group(2).strip()))
    
    return sorted(companies, key=lambda x: x[0])


def main() -> int:
    """Run validation checks."""
    errors = []
    warnings = []
    
    print("=" * 60)
    print("CV Sync Validation")
    print("=" * 60)
    
    # ── Read files ──
    if not CV_TS.exists():
        errors.append(f"cv.ts not found at {CV_TS}")
        print(f"\n❌ {errors[-1]}")
        return 1
    
    if not CV_TRANS_TS.exists():
        errors.append(f"cv_translations.ts not found at {CV_TRANS_TS}")
        print(f"\n❌ {errors[-1]}")
        return 1
    
    if not GEN_PDF_PY.exists():
        errors.append(f"generate_cv_pdfs.py not found at {GEN_PDF_PY}")
        print(f"\n❌ {errors[-1]}")
        return 1
    
    cv_content = CV_TS.read_text()
    trans_content = CV_TRANS_TS.read_text()
    pdf_content = GEN_PDF_PY.read_text()
    
    # ── Check cv.ts ──
    print("\n1. Checking cv.ts (source of truth)...")
    companies = extract_companies_from_cv_ts(cv_content)
    cv_count = len(companies)
    
    print(f"   Found {cv_count} experience entries:")
    for i, (company, role, start) in enumerate(companies):
        print(f"     [{i}] {company} — {role} ({start})")
    
    if cv_count != EXPECTED_COUNT:
        errors.append(f"cv.ts has {cv_count} entries, expected {EXPECTED_COUNT}")
    else:
        print(f"   ✓ Count matches expected ({EXPECTED_COUNT})")
    
    # ── Check cv_translations.ts ──
    print("\n2. Checking cv_translations.ts...")
    
    es_indices = extract_translation_indices(trans_content, "es")
    de_indices = extract_translation_indices(trans_content, "de")
    
    expected_indices = set(range(EXPECTED_COUNT))
    
    print(f"   Spanish (es): found indices {sorted(es_indices)}")
    missing_es = expected_indices - es_indices
    extra_es = es_indices - expected_indices
    if missing_es:
        errors.append(f"cv_translations.ts ES missing indices: {sorted(missing_es)}")
    if extra_es:
        warnings.append(f"cv_translations.ts ES has extra indices: {sorted(extra_es)}")
    if not missing_es and not extra_es:
        print(f"   ✓ Spanish has all {EXPECTED_COUNT} indices")
    
    print(f"   German (de): found indices {sorted(de_indices)}")
    missing_de = expected_indices - de_indices
    extra_de = de_indices - expected_indices
    if missing_de:
        errors.append(f"cv_translations.ts DE missing indices: {sorted(missing_de)}")
    if extra_de:
        warnings.append(f"cv_translations.ts DE has extra indices: {sorted(extra_de)}")
    if not missing_de and not extra_de:
        print(f"   ✓ German has all {EXPECTED_COUNT} indices")
    
    # ── Check generate_cv_pdfs.py ──
    print("\n3. Checking generate_cv_pdfs.py...")
    
    ach_es_count = count_ach_entries(pdf_content, "ACH_ES")
    ach_de_count = count_ach_entries(pdf_content, "ACH_DE")
    
    print(f"   ACH_ES: {ach_es_count} entries")
    if ach_es_count != EXPECTED_COUNT:
        errors.append(f"ACH_ES has {ach_es_count} entries, expected {EXPECTED_COUNT}")
    else:
        print(f"   ✓ ACH_ES count matches expected ({EXPECTED_COUNT})")
    
    print(f"   ACH_DE: {ach_de_count} entries")
    if ach_de_count != EXPECTED_COUNT:
        errors.append(f"ACH_DE has {ach_de_count} entries, expected {EXPECTED_COUNT}")
    else:
        print(f"   ✓ ACH_DE count matches expected ({EXPECTED_COUNT})")
    
    # ── Cross-reference company names ──
    print("\n4. Cross-referencing company names...")
    
    ach_es_companies = extract_ach_company_comments(pdf_content, "ACH_ES")
    
    if len(companies) == len(ach_es_companies):
        mismatches = []
        for i, (cv_company, _, _) in enumerate(companies):
            ach_idx, ach_company = ach_es_companies[i] if i < len(ach_es_companies) else (-1, "")
            # Normalize for comparison (strip parentheses content)
            cv_norm = cv_company.lower().strip()
            ach_norm = ach_company.lower().strip()
            if cv_norm != ach_norm:
                mismatches.append(f"Index {i}: cv.ts='{cv_company}' vs ACH='{ach_company}'")
        
        if mismatches:
            for m in mismatches:
                warnings.append(f"Company name mismatch: {m}")
                print(f"   ⚠ {m}")
        else:
            print(f"   ✓ All company names match between cv.ts and generate_cv_pdfs.py")
    else:
        warnings.append("Cannot cross-reference: entry counts differ")
    
    # ── Summary ──
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    
    if errors:
        print(f"\n❌ ERRORS ({len(errors)}):")
        for e in errors:
            print(f"   • {e}")
    
    if warnings:
        print(f"\n⚠ WARNINGS ({len(warnings)}):")
        for w in warnings:
            print(f"   • {w}")
    
    if not errors and not warnings:
        print("\n✓ All CV files are synchronized!")
    
    print()
    
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
