import json
from pathlib import Path

BANK = Path(__file__).resolve().parents[2] / "GES-C01_Exam_Sample_Questions.json"
data = json.loads(BANK.read_text(encoding="utf-8"))

print("=== Buscando preguntas sobre 'entity' ===")
for q in data["questions"]:
    qtext = q.get("question", "").lower()
    if "entity" in qtext:
        print(f"\nID: {q['id']}")
        print(f"Q: {q.get('question', '')[:200]}")
        print(f"Correct: {q.get('correctAnswer')}")
        print(f"Explanation: {q.get('explanation', '')[:200]}")

print("\n=== Buscando preguntas con EXTRACT_ANSWER ===")
for q in data["questions"]:
    qtext = q.get("question", "").lower()
    opts = str(q.get("options", {})).lower()
    expl = q.get("explanation", "").lower()
    if "extract_answer" in qtext or "extract_answer" in opts or "extract_answer" in expl:
        print(f"\nID: {q['id']}")
        print(f"Q: {q.get('question', '')[:150]}")
        print(f"Correct: {q.get('correctAnswer')}")

print("\n=== Buscando preguntas potencialmente problemáticas (funciones Cortex) ===")
keywords = ["complete", "sentiment", "summarize", "translate", "extract", "classify", "embed"]
issues = []
for q in data["questions"]:
    qtext = q.get("question", "").lower()
    expl = q.get("explanation", "").lower()
    # Buscar preguntas donde la explicación menciona funciones que no existen
    if "entity_extract" in expl or "parse_text" in expl:
        issues.append((q["id"], "References non-existent function"))
    # Buscar respuestas que dicen B es EXTRACT_ANSWER para NER
    if "named entity" in qtext and q.get("correctAnswer") == "B":
        issues.append((q["id"], "Possible wrong answer for NER question"))

for qid, issue in issues:
    print(f"  ID {qid}: {issue}")

print("\nDone.")
