from pathlib import Path

from oai_code_evaluator.cli import load_input
from oai_code_evaluator.config_loader import load_config_dir, validate_bundle
from oai_code_evaluator.evaluator import Evaluator


def _run(sample_name="sample_submission.json"):
    root = Path(__file__).parent.parent
    sample = root / "samples" / sample_name
    data = load_input(sample)
    bundle = validate_bundle(load_config_dir(root / "config_samples"))
    ev = Evaluator(bundle)
    return ev.evaluate(data)


def test_fired_rules_structure():
    result = _run()
    # fired_rules should be present (may be empty depending on sample content)
    assert hasattr(result, "fired_rules")
    assert isinstance(result.fired_rules, list)
    # Rules may or may not fire; if they do, structure must have id and actions
    for r in result.fired_rules:
        assert "id" in r and "actions" in r


def test_schema_validation_passes():
    # Just loading config triggers validation via validate_bundle
    root = Path(__file__).parent.parent
    bundle = validate_bundle(load_config_dir(root / "config_samples"))
    assert bundle.dimensions
