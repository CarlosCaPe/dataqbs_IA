import json
import re
from pathlib import Path

BANK = Path(__file__).resolve().parents[2] / "GES-C01_Exam_Sample_Questions.json"
data = json.loads(BANK.read_text(encoding="utf-8"))

print("Checking for questions that would trigger fallback options...")
for i, q in enumerate(data["questions"]):
    qid = q.get("id")
    opts = q.get("options", {})
    
    if opts and isinstance(opts, dict) and len(opts) >= 2:
        first_val = list(opts.values())[0].strip().lower()
        # Check for actual placeholders only
        is_placeholder = bool(re.match(r'^option\s*[a-e]\.?$', first_val)) or first_val.startswith('[ver pdf')
        if is_placeholder:
            print(f"  Index {i}, ID {qid}: Placeholder detected")
            print(f"    First val: {first_val[:60]}")
    else:
        print(f"  Index {i}, ID {qid}: Missing/invalid options structure")
        print(f"    options type: {type(opts)}, len: {len(opts) if opts else 0}")

print("\nDone.")
