# oai_code_evaluator

Evaluador configurable (rule‑engine declarativo) que asiste al revisor humano sobre una *submission* (prompt + respuestas de modelo + ranking + calificaciones iniciales + rewrite). No sustituye criterio experto: propone ajustes y genera trazabilidad.

## Objetivos y Alcance

Automatiza:
- Ajuste suave de dimensiones (pull hacia ideales + reglas de ajuste incremental).
- Evaluación de reglas declarativas (`rules.yaml`) con explicación (`fired_rules`).
- Normalización de ranking y generación de feedback.
- Transformaciones del rewrite (nota por longitud, cierre, etc.).
- Validación mínima de metadatos del prompt.
- Acumulación de `score`, `flags` y `label` genérica (thresholds declarados, no clasificación de dominios/email).
- Generación de metadatos de auditoría (`rule_version`, `config_hash`, señales básicas).

Responsabilidad HUMANA (no delegada):
- Confirmar o rechazar ajustes de dimensiones frente a la rúbrica oficial.
- Ajustar manualmente comentarios para feedback final a publicar.
- Interpretar `label` como sugerencia interna, no como decisión de producción.
- Aplicar guías de clasificación de correos (Scam/Sus/Spam/Clean/Unknown) — fuera de alcance actual.
- Mantener y versionar el contenido de reglas YAML asegurando calidad/consistencia.

Explícitamente NO hace:
- Detección de phishing o spam real (no parsea headers, dominios, enlaces).
- Ejecución de código arbitrario ni acceso a red.
- Inferencia automática de justificaciones semánticas extensas.

## Instalación rápida

```bash
poetry install
```

## Uso

Ejecutar con la muestra incluida:

```bash
poetry run oai-eval samples/sample_submission.json --out report.json
```

Salida esperada (fragmento):
```json
{
  "corrected_ratings": {"accuracy": {"original": 5.0, "updated": 5.0, ...}},
  "corrected_ranking": ["resp_b", "resp_a"],
  "ranking_feedback": "Ranking ajustado ...",
  "rewrite_final": "Dijkstra halla...",
  "prompt_feedback": "Prompt con etiquetas claras.",
  "global_summary": "Correcciones aplicadas ..."
}
```

## Flujo Operativo Recomendado
1. Preparar `submission` (JSON/YAML) con campos requeridos.
2. Ejecutar:
  ```bash
  poetry run oai-eval samples/sample_submission.json --config-dir config_samples --out result.json
  ```
3. Revisar `fired_rules` y `corrected_ratings` (¿algún ajuste inesperado?).
4. Revisor humano valida/edita (fuera de la herramienta) antes de consolidar.
5. Para auditoría mínima: guardar `result.json` + hash (`meta.config_hash`).
6. Para análisis de motor únicamente: usar `--explain-json explain.json`.

## Roadmap (futuro sugerido)
- Enforce de justificación mínima si |Δ| supera umbral.
- Interfaz interactiva (aceptar/descartar por regla).
- Módulo independiente de clasificación email con señales anti-phishing.
- Firma y timestamping de resultados.

## Estructura

```
oai_code_evaluator/
  oai_code_evaluator/
    cli.py
    evaluator.py
    logging_utils.py
    models.py
    rubric.py
  samples/
    sample_submission.json
  pyproject.toml
```

## Notas
- Ajuste base en `rubric.py` + reglas; cambios delicados deben pasar por revisión.
- Dimensiones: Instructions, Accuracy, Optimality, Presentation, Freshness.
- Logging: `--log-file` para traza reproducible.
- Integridad: `config_hash` = SHA256 de todos los YAML concatenados ordenados.

MIT License.

## Formatos de Configuración (YAML)

El evaluador puede ingerir un directorio (`--config-dir`) con los siguientes archivos:

### 1. dimensions.yaml
Define ideales, tolerancias y parámetros de ajuste de cada dimensión.
```yaml
scale: [0,5]
dimensions:
  accuracy:
    ideal: 4.2
    tolerance: 1.2
    weight: 1.3
adjustment:
  pull_fraction: 0.4
  round: 2
validation:
  require_justification_if_delta_ge: 0.75
```
Campos:
- `dimensions.<dim>.ideal` y `tolerance`: límite para considerar valor “aceptable”.
- `pull_fraction`: fracción usada para mover puntuaciones fuera de tolerancia hacia el ideal.
- `weight`: reservado para futuros cálculos agregados.

### 2. ranking.yaml
```yaml
require_all_ids: true
allow_duplicates: false
corrections:
  append_missing: true
feedback_templates:
  complete: "Ranking incluye todas las respuestas sin duplicados."
  missing_ids: "Se añadieron IDs faltantes al ranking."
  had_duplicates: "Se eliminaron duplicados en el ranking."
```
Lógica:
- Siempre se normaliza el ranking a un conjunto único de IDs válidos.
- Si faltan IDs y `append_missing`=true se añaden al final.

### 3. prompt.yaml
```yaml
required_fields: [prompt, category, subcategory, difficulty]
label_checks:
  category_allow: [algorithms, data, infra]
  difficulty_allow: [easy, medium, hard]
feedback:
  ok: "Prompt con etiquetas claras."
  missing_field: "Faltan campos obligatorios en el prompt: {missing}."
  invalid_label: "Etiqueta fuera de catálogo: {field}={value}."
```
Síntesis: valida metadatos obligatorios y catálogos permitidos.

### 4. rewrite.yaml
```yaml
min_length: 60
add_note_if_short: true
note_text: "Nota: ampliar detalles para cubrir completamente la solución según la documentación."
postprocessors:
  - type: ensure_period
  - type: trim_spaces
```
La lógica actual usa `min_length` y agrega nota si el texto es breve. `postprocessors` es extensible.

### 5. rules.yaml
Estructura de motor declarativo. Bloques principales: `rating_rules`, `ranking_rules`, `rewrite_rules`.

Cada regla:
```yaml
- id: nombre_unico
  when: { ... condiciones ... }
  actions: { ... efectos ... }
```

Condiciones soportadas (en `when`):
- `response_contains_any: [str, ...]` — Alguna palabra/substring aparece en cualquier respuesta o rewrite.
- `preferred_rewrite_missing_substring: [str, ...]` — Todas las substrings listadas están ausentes (modo penalización).
- `rewrite_regex_any: [pat1, pat2]` — Al menos un patrón regex casa contra el rewrite.
- `not_contains_any: [str, ...]` — Si alguna aparece, la regla NO se dispara.
- `min_total_length: N` / `max_total_length: N` — Longitud agregada (respuestas + rewrite).
- `any_of: [ {sub-condiciones}, {sub-condiciones} ]` — OR lógico: basta con que un bloque interno se cumpla.
- `dimension_gt: { accuracy: 4.5 }` — Requiere que la dimensión indicada sea estrictamente mayor al umbral (usa valores originales de entrada).
- `dimension_lt: { optimality: 2.5 }` — Requiere que la dimensión sea menor al umbral.

Acciones (en `actions`):
- `adjust_dimension: { dimension: accuracy, delta: -0.5 }` — Suma delta (positivo o negativo) a la dimensión.
- `add_comment: "Texto"` — Agrega comentario global al resumen.
- `add_comment_template: "Signal eficiencia detectada (length_total={{signals.length_total}})."` — Renderiza plantilla Jinja2 con contexto (`signals`, `detail`, `corrected`).
- `increment_score: 2` — Acumula puntaje para decisión final.
- `set_flag: low_accuracy` — Marca un flag booleano en el estado.
- `assign_label: needs_review` — Fija etiqueta preliminar (puede sobrescribirse por thresholds de score).
- (Rewrite rules) `append_text: "."` / `append_note: true` — Modifican el rewrite final.

Opciones globales (`options` en `rules.yaml`):
```yaml
options:
  dedupe_comments: true    # evita comentarios repetidos
  stop_after_first: false  # si true, detiene evaluación de reglas tras la primera que dispare
  default_label: neutral   # etiqueta base si no hay asignaciones
```

Ejemplo con OR + longitud mínima:
```yaml
- id: optimality_or_accuracy_guard
  when:
    any_of:
      - { response_contains_any: ["heap", "cola de prioridad"] }
      - { response_contains_any: ["priority queue", "O(E log V)"] }
    min_total_length: 120
  actions:
    add_comment: "Se reconoce mención de estructura eficiente o complejidad explícita (regla OR)."
```

### Fase de Decisión y Score
El motor ahora ejecuta fases separadas:
1. Preprocesamiento (`_preprocess`): genera señales (longitudes, conteos) sin mutar estado.
2. Ajuste de dimensiones.
3. Reglas de rating (aplican acciones, suman score, flags, label preliminar).
4. Normalización ranking.
5. Mejora rewrite.
6. Validación prompt.
7. Decisión final: se aplican `decision.score_thresholds` para derivar `label` si `score` alcanza umbrales.

Ejemplo en `rules.yaml`:
```yaml
decision:
  score_thresholds:
    excellent: 5
    good: 3
    neutral: 0
    weak: -1
```
Se evalúan en orden descendente de puntaje mínimo.

### Meta y Auditoría
El resultado incluye `meta` con:
```json
{
  "rule_version": 2,
  "config_hash": "<sha256>",
  "signals": {"length_total": 345, "response_count": 2}
}
```
`config_hash` permite verificar integridad exacta de los YAML (diferente hash => configuración modificada).

### Nuevo flag CLI: --explain-json
Permite exportar únicamente el árbol de reglas disparadas / estado de decisión:
```bash
poetry run oai-eval samples/sample_submission.json \
  --config-dir config_samples \
  --explain-json explain.json
```
Contenido ejemplo:
```json
{
  "fired_rules": [ {"id": "scoring_positive_signal", "actions": [...]} ],
  "score": 2.0,
  "flags": {"low_accuracy": true},
  "label": "needs_review",
  "meta": {"rule_version": 2, "config_hash": "..."}
}
```

### Plantillas Jinja2 en Comentarios
Disponible en `add_comment_template`. Variables:
- `signals.length_total`
- `signals.response_count`
- `detail` (estructura de condiciones evaluadas)
- `corrected` (mapa dimensión->valor ajustado)

### Explicabilidad (`fired_rules`)
Cada entrada incluye: id, tipo, detalle de condiciones evaluadas y acciones aplicadas.
```json
{
  "id": "lower_accuracy_if_no_example",
  "type": "rating",
  "detail": { ... condiciones evaluadas ... },
  "actions": [ { "adjust_dimension": {"dimension": "accuracy", "from": 5.0, "to": 4.5, "delta": -0.5} } ]
}
```

### Limitaciones y Compliance
- No clasificación phishing/spam (requiere módulo separado + señales específicas).
- No eval de código ni acceso externo.
- Plantillas controladas (contexto interno, sin ejecutar código Python arbitrario).
- `label` generada es indicativa y debe revisarse manualmente.

### Validación de Esquema
Cada YAML se valida contra un JSON Schema interno (ver `schemas.py`). Un error lanza `ValueError` con mensaje de detalle.

## Flag CLI relevantes
- `--config-dir DIR` Ruta a YAMLs.
- `--report-md salida.md` Genera reporte Markdown.
- `--log-file log.txt` Logging adicional.

## Ejecución con configuración personalizada
```bash
poetry run oai-eval samples/sample_submission.json \
  --config-dir config_samples \
  --out result.json \
  --report-md result.md
```

