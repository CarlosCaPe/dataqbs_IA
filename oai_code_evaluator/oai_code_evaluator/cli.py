from __future__ import annotations
import argparse
import json
from pathlib import Path
from typing import Any
import yaml

from .logging_utils import setup_logger
from .models import (
    ModelResponse,
    AttemptRatings,
    AttemptSubmission,
    EvaluationInput,
)
from .evaluator import Evaluator
from .config_loader import load_config_dir, validate_bundle


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
    parser = argparse.ArgumentParser(description="Simula el rol de revisor para submissions Outlier.ai LATAM")
    parser.add_argument("input", type=Path, help="Ruta a JSON/YAML con la submission prellenada")
    parser.add_argument("--log-file", dest="log_file", type=Path, default=None, help="Archivo de log opcional")
    parser.add_argument("--out", dest="out", type=Path, default=None, help="Ruta de salida JSON con resultados")
    parser.add_argument("--config-dir", dest="config_dir", type=Path, default=Path("config_samples"), help="Directorio con archivos YAML de configuración")
    parser.add_argument("--report-md", dest="report_md", type=Path, default=None, help="Ruta para generar reporte Markdown")
    parser.add_argument("--fail-on-invalid", action="store_true", help="Falla si la configuración no es válida")
    parser.add_argument("--explain-json", dest="explain_json", type=Path, default=None, help="Exporta solo árbol fired_rules + meta y termina")
    args = parser.parse_args()

    logger = setup_logger(args.log_file)
    logger.info("Cargando submission de entrada…")

    data = load_input(args.input)
    # Cargar configuración
    config_bundle = None
    if args.config_dir and args.config_dir.exists():
        config_bundle = validate_bundle(load_config_dir(args.config_dir))
        logger.info("Configuración cargada desde %s", args.config_dir)
    else:
        logger.warning("No se encontró config_dir %s, usando heurísticas por defecto", args.config_dir)

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
    logger.info("Resumen global: %s", result.global_summary)
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
            f"# Evaluación",
            "## Resumen",
            result.global_summary,
            "## Prompt Feedback",
            result.prompt_feedback,
            "## Ranking",
            result.ranking_feedback,
            "",
            "| Dimensión | Original | Ajustado | Racional |",
            "|-----------|----------|----------|----------|",
        ]
        for dim, corr in result.corrected_ratings.items():
            lines.append(f"| {dim} | {corr.original:.2f} | {corr.updated:.2f} | {corr.rationale} |")
        lines.append("\n## Rewrite Final\n")
        lines.append("````\n" + result.rewrite_final + "\n````")
        args.report_md.write_text("\n".join(lines), encoding="utf-8")
        logger.info("Reporte Markdown escrito en %s", args.report_md)


if __name__ == "__main__":  # pragma: no cover
    main()
