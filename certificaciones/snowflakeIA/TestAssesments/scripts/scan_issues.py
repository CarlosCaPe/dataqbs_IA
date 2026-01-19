import json
from pathlib import Path

BANK = Path(__file__).resolve().parents[2] / "GES-C01_Exam_Sample_Questions.json"

data = json.loads(BANK.read_text(encoding="utf-8"))
issues = []

for q in data["questions"]:
    qid = q.get("id")
    exp = str(q.get("explanation", "")).strip()
    question_text = q.get("question", "")
    options = q.get("options", {})
    options_str = " ".join(str(v) for v in options.values())

    # Short or missing explanation
    if len(exp) < 30:
        issues.append(f"id={qid}: short explanation ({repr(exp[:40])})")

    # OCR typos
    if "Document Al" in question_text:
        issues.append(f"id={qid}: OCR typo 'Document Al' in question")
    if "POF" in options_str:
        issues.append(f"id={qid}: OCR typo 'POF' in options")
    if "fail'" in question_text:
        issues.append(f"id={qid}: OCR artifact \"fail'\" in question")

print(f"Scanned {len(data['questions'])} questions")
print(f"Issues found: {len(issues)}")
for i in issues:
    print(f"  {i}")
