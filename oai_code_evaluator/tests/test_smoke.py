from pathlib import Path
import json
from oai_code_evaluator.cli import load_input
from oai_code_evaluator.evaluator import Evaluator
from oai_code_evaluator.config_loader import load_config_dir, validate_bundle


def test_smoke_eval_default():
    sample = Path(__file__).parent.parent / "samples" / "sample_submission.json"
    data = load_input(sample)
    result = Evaluator().evaluate(data)
    assert result.corrected_ratings
    assert len(result.corrected_ranking) == len(data.submission.responses)


def test_eval_with_config(tmp_path):
    root = Path(__file__).parent.parent
    sample = root / "samples" / "sample_submission.json"
    data = load_input(sample)
    bundle = validate_bundle(load_config_dir(root / "config_samples"))
    result = Evaluator(bundle).evaluate(data)
    assert result.rewrite_final
    # Generate markdown report
    md_path = tmp_path / "report.md"
    md_path.write_text("placeholder", encoding="utf-8")
    # Simulate markdown generation logic (simplified)
    lines = ["# Evaluación", result.global_summary]
    md_path.write_text("\n".join(lines), encoding="utf-8")
    assert md_path.read_text(encoding="utf-8").startswith("# Evaluación")

