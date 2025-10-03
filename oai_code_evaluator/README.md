# oai_code_evaluator

Herramienta CLI para simular la experiencia real de un REVISOR (reviewer) evaluando una sumisión prellenada (prompt + respuestas de modelo + ranking + calificaciones iniciales + rewrite) tal como se describe en el flujo LATAM.

## Propósito

Permite cargar un archivo JSON/YAML que representa la sumisión entregada al revisor y producir una salida estructurada con:
- Correcciones numéricas por dimensión (Instructions, Accuracy, Optimality, Presentation, Freshness)
- Feedback/rationale de ranking
- Prompt feedback
- Reescritura final refinada
- Resumen global

La lógica actual es un esqueleto heurístico: NO reemplaza criterio experto ni las rúbricas oficiales. Sirve como base para extender reglas, validaciones, integración de guías versionadas y, eventualmente, ejecución segura de código para validar evidencia.

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

## Extensiones futuras sugeridas

1. Cargar rúbricas oficiales (JSON versionado) y validar rangos/justificaciones obligatorias.
2. Motor de reglas (ej. JSON Schema + expresiones) para aplicar ajustes más explicables.
3. Validación de ejecución de código en sandbox aislado (timeout + resource limits).
4. Generación de un reporte Markdown/HTML comparativo.
5. Modo interactivo para que el revisor confirme o edite ajustes sugeridos.
6. Integración con almacenamiento de evidencias (hashes, timestamps, firma).

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
- El evaluador actual ajusta valores desplazados hacia un ideal heurístico. Ajustar la lógica en `rubric.py` según necesidades.
- Los nombres de dimensiones siguen la traducción: Instructions, Accuracy, Optimality, Presentation, Freshness (Actualización).
- `--log-file` permite registrar salida detallada para auditoría.

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

### Explain de Reglas
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

### Limitaciones y Compliance
El sistema se limita a:
- Ajustar dimensiones y producir feedback textual.
- Acumular score y derivar una etiqueta interna genérica (no implementa todavía categorías scam/sus/spam/clean/unknown del dominio de emails — solo ejemplo neutral).
- No ejecuta acciones fuera de las definidas ni realiza clasificación de emails completa.

Para extender a un clasificador de emails multi-clase se requeriría una capa adicional de extracción de señales específicas (headers, dominios, patrones regex de phishing) y un conjunto de reglas con prioridades (ver `rules_summary.txt`). Esto NO está incluido por diseño para mantener alcance controlado.
El resultado expone `fired_rules`: lista ordenada, cada entrada incluye:
```json
{
  "id": "lower_accuracy_if_no_example",
  "type": "rating",
  "detail": { ... condiciones evaluadas ... },
  "actions": [ { "adjust_dimension": {"dimension": "accuracy", "from": 5.0, "to": 4.5, "delta": -0.5} } ]
}
```

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

