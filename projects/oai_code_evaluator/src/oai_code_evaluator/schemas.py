"""JSON Schemas para validar archivos YAML de configuración."""
from __future__ import annotations

DIMENSIONS_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
        "scale": {"type": "array", "items": {"type": "number"}, "minItems": 2, "maxItems": 2},
        "dimensions": {
            "type": "object",
            "patternProperties": {
                ".+": {
                    "type": "object",
                    "properties": {
                        "ideal": {"type": "number"},
                        "tolerance": {"type": "number"},
                        "weight": {"type": "number"},
                    },
                    "required": ["ideal", "tolerance"],
                }
            },
            "additionalProperties": False,
        },
        "adjustment": {
            "type": "object",
            "properties": {
                "pull_fraction": {"type": "number", "minimum": 0, "maximum": 1},
                "round": {"type": "integer", "minimum": 0, "maximum": 4},
            },
        },
    },
    "required": ["dimensions"],
}

RANKING_SCHEMA = {
    "type": "object",
    "properties": {
        "require_all_ids": {"type": "boolean"},
        "allow_duplicates": {"type": "boolean"},
        "rationale": {"type": "object"},
        "corrections": {"type": "object"},
        "feedback_templates": {"type": "object"},
    },
}

PROMPT_SCHEMA = {
    "type": "object",
    "properties": {
        "required_fields": {"type": "array", "items": {"type": "string"}},
        "label_checks": {"type": "object"},
        "feedback": {"type": "object"},
    },
}

REWRITE_SCHEMA = {
    "type": "object",
    "properties": {
        "min_length": {"type": "integer", "minimum": 0},
        "add_note_if_short": {"type": "boolean"},
        "note_text": {"type": "string"},
        "postprocessors": {"type": "array"},
    },
}

RULES_SCHEMA = {
    "type": "object",
    "properties": {
        "version": {"type": "integer"},
        "rating_rules": {"type": "array"},
        "ranking_rules": {"type": "array"},
        "rewrite_rules": {"type": "array"},
        "feedback_priorities": {"type": "object"},
        "options": {
            "type": "object",
            "properties": {
                "dedupe_comments": {"type": "boolean"},
                "stop_after_first": {"type": "boolean"},
                "score_thresholds": {"type": "object"},
                "default_label": {"type": "string"}
            },
        },
        "decision": {
            "type": "object",
            "properties": {
                "score_thresholds": {"type": "object"},
                "label_priority": {"type": "array", "items": {"type": "string"}},
            },
        },
    },
}

SCHEMAS = {
    "dimensions": DIMENSIONS_SCHEMA,
    "ranking": RANKING_SCHEMA,
    "prompt": PROMPT_SCHEMA,
    "rewrite": REWRITE_SCHEMA,
    "rules": RULES_SCHEMA,
}
