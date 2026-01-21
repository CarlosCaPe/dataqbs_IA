"""
Audita inconsistencias entre explicaciones y respuestas correctas.
Busca casos donde la explicación menciona opciones que no coinciden con correctAnswer.
"""
import json
import re

# Cargar preguntas
with open("../../GES-C01_Exam_Sample_Questions.json", "r", encoding="utf-8") as f:
    data = json.load(f)

questions = data if isinstance(data, list) else data.get("questions", [])

print("=" * 70)
print("AUDITORÍA DE CONSISTENCIA: EXPLICACIONES vs RESPUESTAS CORRECTAS")
print("=" * 70)

issues = []

for q in questions:
    qid = q.get("id")
    correct = q.get("correctAnswer", "")
    explanation = q.get("explanation", "")
    options = q.get("options", {})
    
    # Parsear las letras correctas
    correct_letters = set(correct.replace(" ", "").split(","))
    
    # Buscar patrones en la explicación que indiquen opciones correctas/incorrectas
    # Patrones comunes: "(A) is correct", "Option A is correct", "(B) is incorrect"
    
    # Encontrar letras mencionadas como correctas en la explicación
    correct_patterns = [
        r'\(([A-E])\)\s+(?:is\s+)?correct',  # (A) is correct, (A) correct
        r'Option\s+([A-E])\s+is\s+correct',  # Option A is correct
        r'\(([A-E])\)[^.]*(?:TRUE|true|correct)',  # (A) ... TRUE/correct
    ]
    
    # Encontrar letras mencionadas como incorrectas
    incorrect_patterns = [
        r'\(([A-E])\)\s+is\s+incorrect',  # (A) is incorrect
        r'Option\s+([A-E])\s+is\s+incorrect',  # Option A is incorrect
        r'\(([A-E])\)[^.]*(?:FALSE|false|incorrect|wrong)',  # (A) ... FALSE/incorrect
    ]
    
    mentioned_correct = set()
    mentioned_incorrect = set()
    
    for pattern in correct_patterns:
        matches = re.findall(pattern, explanation, re.IGNORECASE)
        mentioned_correct.update(matches)
    
    for pattern in incorrect_patterns:
        matches = re.findall(pattern, explanation, re.IGNORECASE)
        mentioned_incorrect.update(matches)
    
    # Normalizar a mayúsculas
    mentioned_correct = {x.upper() for x in mentioned_correct}
    mentioned_incorrect = {x.upper() for x in mentioned_incorrect}
    
    # Detectar problemas
    problems = []
    
    # 1. Explicación dice que una opción es correcta pero no está en correctAnswer
    false_correct = mentioned_correct - correct_letters
    if false_correct:
        problems.append(f"Explicación dice {false_correct} correcta(s) pero correctAnswer={correct}")
    
    # 2. Explicación dice que una opción es incorrecta pero SÍ está en correctAnswer
    false_incorrect = mentioned_incorrect & correct_letters
    if false_incorrect:
        problems.append(f"Explicación dice {false_incorrect} incorrecta(s) pero ESTÁ en correctAnswer={correct}")
    
    # 3. correctAnswer incluye opciones que la explicación dice son incorrectas
    should_be_incorrect = mentioned_incorrect & correct_letters
    if should_be_incorrect:
        problems.append(f"CONFLICTO: {should_be_incorrect} marcada correcta pero explicación dice incorrecta")
    
    if problems:
        issues.append({
            "id": qid,
            "correctAnswer": correct,
            "problems": problems,
            "explanation": explanation[:200] + "..." if len(explanation) > 200 else explanation
        })

print(f"\nTotal de preguntas analizadas: {len(questions)}")
print(f"Preguntas con posibles inconsistencias: {len(issues)}")
print()

if issues:
    print("=" * 70)
    print("DETALLES DE INCONSISTENCIAS ENCONTRADAS")
    print("=" * 70)
    for issue in issues:
        print(f"\n--- ID {issue['id']} ---")
        print(f"correctAnswer: {issue['correctAnswer']}")
        for p in issue['problems']:
            print(f"  ⚠️  {p}")
        print(f"Explicación: {issue['explanation']}")
else:
    print("✅ No se encontraron inconsistencias obvias.")

print("\n" + "=" * 70)
print("FIN DE AUDITORÍA")
print("=" * 70)
