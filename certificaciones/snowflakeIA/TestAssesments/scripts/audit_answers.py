"""
Auditoría exhaustiva del banco de preguntas GES-C01.
Busca inconsistencias entre respuestas/explicaciones y la documentación oficial de Snowflake.
"""
import json
from pathlib import Path

BANK = Path(__file__).resolve().parents[2] / "GES-C01_Exam_Sample_Questions.json"
data = json.loads(BANK.read_text(encoding="utf-8"))

issues = []

# Funciones que NO existen en Snowflake Cortex (según docs oficiales enero 2026)
NON_EXISTENT_FUNCTIONS = [
    "entity_extract",
    "parse_text",  # Es PARSE_DOCUMENT, no PARSE_TEXT
    "ner",
    "named_entity",
]

# Funciones reales y su propósito correcto
FUNCTION_PURPOSES = {
    "extract_answer": "extractive question answering (responder preguntas de un texto)",
    "complete": "generación de texto con LLM",
    "ai_complete": "generación de texto con LLM (versión actualizada)",
    "summarize": "resumir texto",
    "translate": "traducir texto",
    "sentiment": "análisis de sentimiento",
    "embed_text": "generar embeddings de texto",
    "ai_embed": "generar embeddings (versión actualizada)",
    "ai_extract": "extraer información de texto/archivos (versión actualizada de EXTRACT_ANSWER)",
    "ai_classify": "clasificar texto/imágenes en categorías",
    "ai_filter": "filtrar filas con condiciones de lenguaje natural",
    "parse_document": "extraer texto/layout de documentos",
    "ai_parse_document": "extraer texto/layout de documentos (versión actualizada)",
    "count_tokens": "contar tokens de entrada",
    "ai_count_tokens": "contar tokens (versión actualizada)",
    "entity_sentiment": "sentimiento a nivel de entidad (NO es NER puro)",
}

print("=== AUDITORÍA EXHAUSTIVA DEL BANCO DE PREGUNTAS ===\n")

for q in data["questions"]:
    qid = q["id"]
    qtext = q.get("question", "").lower()
    opts = q.get("options", {})
    opts_text = " ".join(str(v).lower() for v in opts.values())
    expl = q.get("explanation", "").lower()
    correct = q.get("correctAnswer", "")
    
    # 1. Buscar referencias a funciones que no existen
    for func in NON_EXISTENT_FUNCTIONS:
        if func in qtext or func in opts_text or func in expl:
            # Excepciones: si la opción dice que NO existe, está bien
            if "no dedicated" not in opts_text and "does not exist" not in opts_text:
                issues.append((qid, f"Referencias función inexistente: {func}"))
    
    # 2. Pregunta sobre NER con respuesta B (EXTRACT_ANSWER) - INCORRECTO
    if "named entity" in qtext and correct == "B":
        issues.append((qid, "CRÍTICO: Respuesta B para NER - EXTRACT_ANSWER no es para NER"))
    
    # 3. Pregunta menciona entity extraction pero respuesta no es E
    if "entity" in qtext and "extract" in qtext and correct != "E":
        if "entity_sentiment" not in qtext:  # Excluir entity_sentiment
            issues.append((qid, f"Posible error: pregunta sobre entity extraction, respuesta={correct}"))
    
    # 4. Explicación contradice la respuesta
    if "extract_answer" in expl and "question" in expl and correct == "B":
        if "entity" in qtext and "named" in qtext:
            issues.append((qid, "Explicación dice que EXTRACT_ANSWER es para preguntas, pero respuesta B seleccionada para pregunta sobre NER"))
    
    # 5. Buscar opciones que mencionan funciones ficticias como correctas
    if "d" in correct.lower():
        opt_d = opts.get("D", "").lower()
        if "entity_extract" in opt_d:
            issues.append((qid, "CRÍTICO: Opción D menciona ENTITY_EXTRACT (no existe) como correcta"))

# Eliminar duplicados y ordenar
issues = sorted(set(issues), key=lambda x: x[0])

print(f"Total de problemas encontrados: {len(issues)}\n")
for qid, issue in issues:
    print(f"  ID {qid}: {issue}")

# Mostrar detalles de preguntas problemáticas
print("\n=== DETALLES DE PREGUNTAS PROBLEMÁTICAS ===")
problem_ids = set(qid for qid, _ in issues)
for q in data["questions"]:
    if q["id"] in problem_ids:
        print(f"\n--- ID {q['id']} ---")
        print(f"Topic: {q.get('topic')}")
        print(f"Q: {q.get('question', '')[:200]}")
        print(f"Options:")
        for k, v in q.get("options", {}).items():
            marker = " <<<" if k in q.get("correctAnswer", "") else ""
            print(f"  {k}: {v[:80]}{marker}")
        print(f"Correct: {q.get('correctAnswer')}")
        print(f"Explanation: {q.get('explanation', '')[:200]}")

print("\n=== FIN DE AUDITORÍA ===")
