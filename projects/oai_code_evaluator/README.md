# oai_code_evaluator

Configurable evaluator (declarative rule engine) that assists a human reviewer over a submission (prompt + model responses + ranking + initial ratings + rewrite). It does not replace expert judgement: it proposes adjustments and produces traceability.

## Purpose and Scope

Automates:
- Gentle dimension adjustment (pull toward ideals + incremental rule adjustments).
- Declarative rule evaluation (`rules.yaml`) with explanation (`fired_rules`).
- Ranking normalization and feedback generation.
- Rewrite transformations (length note, final punctuation, etc.).
- Basic validation of prompt metadata.
- Accumulation of `score`, `flags` and generic `label` (declared thresholds; no domain/email classification).
- Audit metadata generation (`rule_version`, `config_hash`, basic signals).

Human (non-delegated) responsibilities:
- Accept or reject dimension adjustments against the official rubric.
- Manually refine comments for final feedback publication.
- Treat `label` as internal suggestion, not production decision.
- Apply separate email classification guidelines (Scam/Sus/Spam/Clean/Unknown) — out of scope here.
- Maintain and version YAML rule content ensuring consistency & quality.

Explicitly does NOT:
- Perform real phishing or spam detection (no header/domain/link parsing).
- Execute arbitrary code or reach the network.
- Generate long semantic justifications automatically.

## Quick Install

```bash
poetry install
```

## Usage

Run with included sample:

```bash
poetry run oai-eval samples/sample_submission.json --out report.json
```

Expected output (fragment):
```json
{
  "corrected_ratings": {"accuracy": {"original": 5.0, "updated": 5.0, ...}},
  "corrected_ranking": ["resp_b", "resp_a"],
  "ranking_feedback": "Ranking adjusted ...",
  "rewrite_final": "Dijkstra finds...",
  "prompt_feedback": "Prompt has clear labels.",
  "global_summary": "Adjustments applied ..."
}
```

## Recommended Operational Flow
1. Prepare `submission` (JSON/YAML) with required fields.
2. Run:
  ```bash
  poetry run oai-eval samples/sample_submission.json --config-dir config_samples --out result.json
  ```
3. Inspect `fired_rules` and `corrected_ratings` (any unexpected adjustment?).
4. Human reviewer validates/edits outside the tool.
5. For minimal audit: keep `result.json` + hash (`meta.config_hash`).
6. For engine analysis only: use `--explain-json explain.json`.

## Roadmap (suggested future)
- Enforce justification if |Δ| exceeds threshold.
- Interactive interface (accept/decline per rule).
- Stand‑alone email classification module with anti‑phishing signals.
- Result signing and timestamping.

## Structure

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

## Notes
- Base adjustment in `rubric.py` + rules; sensitive changes need review.
- Dimensions: Instructions, Accuracy, Optimality, Presentation, Freshness.
- Logging: `--log-file` for reproducible trace.
- Integrity: `config_hash` = SHA256 of all YAML dumps sorted.

MIT License.

## Configuration Formats (YAML)

The evaluator consumes a directory (`--config-dir`) with:

### 1. dimensions.yaml
Defines ideals, tolerances and adjustment parameters per dimension.
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
Fields:
- `dimensions.<dim>.ideal` and `tolerance`: acceptable band around the ideal.
- `pull_fraction`: fraction used to pull scores outside tolerance toward the ideal.
- `weight`: reserved for future aggregate computations.

### 2. ranking.yaml
```yaml
require_all_ids: true
allow_duplicates: false
corrections:
  append_missing: true
feedback_templates:
  complete: "Ranking includes all answers without duplicates."
  missing_ids: "Missing IDs were appended to the ranking."
  had_duplicates: "Duplicates were removed from the ranking."
```
Logic:
- Ranking normalized to a unique ordered set of valid response IDs.
- Missing IDs appended if `append_missing` = true.

### 3. prompt.yaml
```yaml
required_fields: [prompt, category, subcategory, difficulty]
label_checks:
  category_allow: [algorithms, data, infra]
  difficulty_allow: [easy, medium, hard]
feedback:
  ok: "Prompt has clear labels."
  missing_field: "Missing required prompt fields: {missing}."
  invalid_label: "Label not in allowed catalog: {field}={value}."
```
Summary: validates mandatory metadata and allowed catalogs.

### 4. rewrite.yaml
```yaml
min_length: 60
add_note_if_short: true
note_text: "Note: expand details to fully cover the solution as per documentation."
postprocessors:
  - type: ensure_period
  - type: trim_spaces
```
Current logic uses `min_length` and appends a note if text is short. `postprocessors` is extensible.

### 5. rules.yaml
Declarative engine structure. Sections: `rating_rules`, `ranking_rules`, `rewrite_rules`.

Each rule:
```yaml
- id: unique_name
  when: { ... conditions ... }
  actions: { ... effects ... }
```

Conditions supported (`when`):
- `response_contains_any: [str, ...]` — Any substring appears in any response or rewrite.
- `preferred_rewrite_missing_substring: [str, ...]` — All listed substrings absent (penalty mode).
- `rewrite_regex_any: [pat1, pat2]` — At least one regex matches the rewrite.
- `not_contains_any: [str, ...]` — If any appears the rule does NOT fire.
- `min_total_length: N` / `max_total_length: N` — Aggregate length (responses + rewrite).
- `any_of: [ {sub-conditions}, {sub-conditions} ]` — Logical OR: one inner block suffices.
- `dimension_gt: { accuracy: 4.5 }` — Dimension strictly greater than threshold.
- `dimension_lt: { optimality: 2.5 }` — Dimension strictly below threshold.

Actions (`actions`):
- `adjust_dimension: { dimension: accuracy, delta: -0.5 }` — Applies delta to dimension.
- `add_comment: "Text"` — Adds global comment to summary.
- `add_comment_template: "Efficiency signal (length_total={{signals.length_total}})."` — Renders Jinja2 template with context (`signals`, `detail`, `corrected`).
- `increment_score: 2` — Adds to cumulative score.
- `set_flag: low_accuracy` — Sets a boolean flag.
- `assign_label: needs_review` — Preliminary label (may be overridden by thresholds).
- (Rewrite rules) `append_text: "."` / `append_note: true` — Modify final rewrite.

Global options (`options` in `rules.yaml`):
```yaml
options:
  dedupe_comments: true    # avoid repeated comments
  stop_after_first: false  # stop evaluation after first fired rule if true
  default_label: neutral   # base label if nothing assigned
```

Example with OR + minimum length:
```yaml
- id: optimality_or_accuracy_guard
  when:
    any_of:
      - { response_contains_any: ["heap", "priority queue"] }
      - { response_contains_any: ["O(E log V)"] }
    min_total_length: 120
  actions:
    add_comment: "Efficient structure mention or explicit complexity recognized (OR rule)."
```

### Decision & Score Phase
Separate phases:
1. Preprocessing (`_preprocess`): derives signals without mutating state.
2. Dimension adjustment.
3. Rating rules (apply actions, accumulate score, flags, preliminary label).
4. Ranking normalization.
5. Rewrite improvement.
6. Prompt validation.
7. Final decision: apply `decision.score_thresholds` if `score` meets thresholds.

Example:
```yaml
decision:
  score_thresholds:
    excellent: 5
    good: 3
    neutral: 0
    weak: -1
```
Evaluated in descending order of minimum score.

### Metadata & Audit
Result includes `meta`:
```json
{
  "rule_version": 2,
  "config_hash": "<sha256>",
  "signals": {"length_total": 345, "response_count": 2}
}
```
`config_hash` ensures integrity (different hash => config changed).

### New CLI flag: --explain-json
Exports only fired rules / decision state:
```bash
poetry run oai-eval samples/sample_submission.json \
  --config-dir config_samples \
  --explain-json explain.json
```
Example content:
```json
{
  "fired_rules": [ {"id": "scoring_positive_signal", "actions": [...]} ],
  "score": 2.0,
  "flags": {"low_accuracy": true},
  "label": "needs_review",
  "meta": {"rule_version": 2, "config_hash": "..."}
}
```

### Jinja2 Templates in Comments
Available via `add_comment_template`. Variables:
- `signals.length_total`
- `signals.response_count`
- `detail` (condition evaluation structure)
- `corrected` (dimension -> updated value)

### Explainability (`fired_rules`)
Each entry includes: id, type, condition detail, applied actions.
```json
{
  "id": "lower_accuracy_if_no_example",
  "type": "rating",
  "detail": { ... conditions ... },
  "actions": [ { "adjust_dimension": {"dimension": "accuracy", "from": 5.0, "to": 4.5, "delta": -0.5} } ]
}
```

### Limitations & Compliance
- No phishing/spam classification.
- No code execution or external access.
- Templates sandboxed (only internal context).
- Generated `label` is advisory and must be reviewed.

### Schema Validation
Each YAML validated against an internal JSON Schema (see `schemas.py`). On error a `ValueError` is raised.

## Relevant CLI Flags
- `--config-dir DIR` YAML path.
- `--report-md output.md` Markdown report.
- `--log-file log.txt` Additional logging.

## Run with custom configuration
```bash
poetry run oai-eval samples/sample_submission.json \
  --config-dir config_samples \
  --out result.json \
  --report-md result.md
```

