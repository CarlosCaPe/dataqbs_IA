#!/usr/bin/env python3
"""Audit + auto-fix question bank formatting issues.

Goals:
- Detect questions that still have embedded options in the `question` text.
- Convert embedded options into structured `options` dict and clean `question`.
- Detect truncation / placeholders / missing option letters referenced by `correctAnswer`.

This script does NOT invent new question content; it only restructures what is already present.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple


JSON_PATH = Path(r"C:\Users\CarlosCarrillo\IA\dataqbs_IA\certificaciones\snowflakeIA\GES-C01_Exam_Sample_Questions.json")


EMBEDDED_OPTION_RE = re.compile(
    r"(?:^|\s)([A-Ea-e])[.\)]\s*(.+?)(?=\s+[A-Ea-e][.\)]\s|\s*$)",
    flags=re.S,
)


def _normalize_ws(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def extract_embedded_options(question_text: str) -> Tuple[str, Dict[str, str]]:
    """Return (clean_question, options) if embedded A–E options exist."""
    matches = EMBEDDED_OPTION_RE.findall(question_text or "")
    if not matches or len(matches) < 2:
        return question_text.strip(), {}

    options: Dict[str, str] = {}
    for letter, opt_text in matches:
        letter_u = letter.upper()
        opt = _normalize_ws(opt_text)
        # Filter generic/corrupt placeholders
        if opt.lower() in {f"option {letter_u.lower()}", f"option{letter_u.lower()}", ""}:
            continue
        options[letter_u] = opt

    # Clean question part before first option marker
    m = re.search(r"\s+[A-Ea-e][.\)]\s", question_text)
    clean_question = question_text[: m.start()].strip() if m else question_text.strip()

    # If options are still not meaningful, return empty
    if len(options) < 2:
        return question_text.strip(), {}

    return clean_question, options


def is_placeholder_options(options: Dict[str, str]) -> bool:
    vals = " ".join(options.values()).lower() if options else ""
    return ("[ver pdf" in vals) or bool(re.search(r"\boption\s+[a-e]\b", vals))


def referenced_letters(correct_answer: str) -> List[str]:
    ca = (correct_answer or "").replace(" ", "")
    if not ca:
        return []
    return [x for x in ca.split(",") if x]


@dataclass
class Issue:
    qid: int
    kind: str
    detail: str = ""


def main() -> int:
    data = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    questions: List[dict] = data.get("questions", [])

    issues: List[Issue] = []
    fixed = 0

    for q in questions:
        qid = int(q.get("id"))
        qtext = q.get("question", "") or ""
        opts = q.get("options")

        # If options are missing/invalid or placeholders, try to extract from question text
        need_extract = (not isinstance(opts, dict) or len(opts) < 2)
        if isinstance(opts, dict) and len(opts) >= 2 and is_placeholder_options(opts):
            need_extract = True

        if need_extract:
            clean_q, extracted = extract_embedded_options(qtext)
            if extracted:
                q["question"] = clean_q
                q["options"] = extracted
                fixed += 1
            else:
                has_markers = bool(re.search(r"\b[A-Ea-e][\)\.]\s", qtext))
                issues.append(Issue(qid, "missing_or_unextractable_options", "markers" if has_markers else "no_markers"))

        # Validate correctAnswer letters exist
        opts2 = q.get("options") if isinstance(q.get("options"), dict) else {}
        missing = [x for x in referenced_letters(q.get("correctAnswer", "")) if x not in opts2]
        if missing:
            issues.append(Issue(qid, "correctAnswer_missing_option_keys", ",".join(missing)))

        # Detect OCR junk in question text
        if re.search(r"\bAnswer:\b", qtext, re.I) or re.search(r"\bExplanation:\b", qtext, re.I):
            issues.append(Issue(qid, "ocr_junk_in_question", "contains Answer:/Explanation:"))

        # Detect likely truncation
        if re.search(r"\bD\s*$", qtext) and (not isinstance(q.get("options"), dict) or len(q.get("options", {})) < 2):
            issues.append(Issue(qid, "likely_truncated", "endswith D"))

    # Save if we fixed anything
    if fixed:
        data["metadata"] = data.get("metadata", {})
        data["metadata"]["lastUpdated"] = "2026-01-19"
        data["metadata"]["autoFixedEmbeddedOptions"] = fixed
        JSON_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    # Print report
    print(f"Auto-fixed embedded options: {fixed}")
    print(f"Remaining issues: {len(issues)}")
    by_kind: Dict[str, int] = {}
    for it in issues:
        by_kind[it.kind] = by_kind.get(it.kind, 0) + 1
    for k, v in sorted(by_kind.items(), key=lambda kv: -kv[1]):
        print(f"  {k}: {v}")

    if issues:
        # show a compact list of the worst offenders
        sample = issues[:40]
        print("Sample:")
        for it in sample:
            print(f"  id={it.qid} kind={it.kind} detail={it.detail}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
