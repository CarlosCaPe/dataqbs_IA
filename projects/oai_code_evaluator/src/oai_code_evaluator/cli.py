from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml

from .config_loader import load_config_dir, validate_bundle
from .evaluator import Evaluator
from .logging_utils import setup_logger
from .models import (
    AttemptRatings,
    AttemptSubmission,
    EvaluationInput,
    ModelResponse,
)


def load_input(path: Path) -> EvaluationInput:
    raw: Any
    if path.suffix.lower() in {".yml", ".yaml"}:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    else:
        raw = json.loads(path.read_text(encoding="utf-8"))

    responses = [ModelResponse(**r) for r in raw["responses"]]
    ratings = AttemptRatings(**raw["ratings"])
    submission = AttemptSubmission(
        prompt=raw["prompt"],
        category=raw.get("category", ""),
        subcategory=raw.get("subcategory", ""),
        difficulty=raw.get("difficulty", ""),
        responses=responses,
        ranking=raw["ranking"],
        ranking_rationale=raw.get("ranking_rationale", ""),
        rewrite_preferred=raw.get("rewrite_preferred", ""),
        ratings=ratings,
        evidence=raw.get("evidence"),
    )
    return EvaluationInput(submission=submission)


def main():  # pragma: no cover - CLI orchestration
    parser = argparse.ArgumentParser(description="Simulate reviewer assistance on a prepared submission")
    parser.add_argument("input", type=Path, help="Path to JSON/YAML submission file")
    parser.add_argument("--log-file", dest="log_file", type=Path, default=None, help="Optional log file path")
    parser.add_argument("--out", dest="out", type=Path, default=None, help="Output JSON result path")
    parser.add_argument("--config-dir", dest="config_dir", type=Path, default=Path("config_samples"), help="Directory with YAML configuration files")
    parser.add_argument("--report-md", dest="report_md", type=Path, default=None, help="Markdown report output path")
    parser.add_argument("--fail-on-invalid", action="store_true", help="Fail fast if configuration invalid")
    parser.add_argument("--explain-json", dest="explain_json", type=Path, default=None, help="Export only fired_rules tree + meta and exit")
    args = parser.parse_args()

    logger = setup_logger(args.log_file)
    logger.info("Loading submission input…")

    data = load_input(args.input)
    # Cargar configuración
    config_bundle = None
    if args.config_dir and args.config_dir.exists():
        config_bundle = validate_bundle(load_config_dir(args.config_dir))
        logger.info("Configuration loaded from %s", args.config_dir)
    else:
        logger.warning("Config dir %s not found, using fallback heuristics", args.config_dir)

    evaluator = Evaluator(config_bundle)
    result = evaluator.evaluate(data)

    if args.explain_json:
        args.explain_json.write_text(
            json.dumps(
                {
                    "fired_rules": result.fired_rules,
                    "score": result.score,
                    "flags": result.flags,
                    "label": result.label,
                    "meta": result.meta,
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        logger.info("Explicación exportada en %s", args.explain_json)
        return

    # Console summary minimal
    logger.info("Global summary: %s", result.global_summary)
    for dim, corr in result.corrected_ratings.items():
        logger.info("%s: %.2f -> %.2f (%s)", dim, corr.original, corr.updated, corr.rationale)

    if args.out:
        args.out.write_text(
            json.dumps(
                {
                    "corrected_ratings": {k: corr.__dict__ for k, corr in result.corrected_ratings.items()},
                    "corrected_ranking": result.corrected_ranking,
                    "ranking_feedback": result.ranking_feedback,
                    "rewrite_final": result.rewrite_final,
                    "prompt_feedback": result.prompt_feedback,
                    "global_summary": result.global_summary,
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        logger.info("Resultado escrito en %s", args.out)

    if args.report_md:
        lines = [
            "# Evaluation",
            "## Summary",
            result.global_summary,
            "## Prompt Feedback",
            result.prompt_feedback,
            "## Ranking",
            result.ranking_feedback,
            "",
            "| Dimension | Original | Adjusted | Rationale |",
            "|-----------|----------|----------|-----------|",
        ]
        for dim, corr in result.corrected_ratings.items():
            lines.append(f"| {dim} | {corr.original:.2f} | {corr.updated:.2f} | {corr.rationale} |")
        lines.append("\n## Rewrite Final\n")
        lines.append("````\n" + result.rewrite_final + "\n````")
        args.report_md.write_text("\n".join(lines), encoding="utf-8")
        logger.info("Reporte Markdown escrito en %s", args.report_md)


if __name__ == "__main__":  # pragma: no cover
    main()
