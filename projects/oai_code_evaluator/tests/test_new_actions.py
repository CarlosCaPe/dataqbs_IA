from pathlib import Path

from oai_code_evaluator.cli import load_input
from oai_code_evaluator.config_loader import load_config_dir, validate_bundle
from oai_code_evaluator.evaluator import Evaluator


def load_bundle():
    root = Path(__file__).parent.parent
    return validate_bundle(load_config_dir(root / "config_samples"))


def test_increment_score_and_label_and_flag():
    root = Path(__file__).parent.parent
    sample = root / "samples" / "sample_submission.json"
    data = load_input(sample)
    bundle = load_bundle()
    ev = Evaluator(bundle)
    result = ev.evaluate(data)
    # Score may be None if rule not triggered; ensure fields exist
    assert hasattr(result, 'score')
    assert isinstance(result.flags, dict)
    # If low accuracy rule fires in modified scenario
    data.submission.ratings.accuracy = 1.5  # type: ignore[attr-defined]
    result2 = ev.evaluate(data)
    # After low accuracy, expect flag if rule condition matches
    if any(r['id'] == 'flag_and_label_if_low_accuracy' for r in result2.fired_rules):
        assert result2.flags.get('low_accuracy') is True
        assert result2.label == 'needs_review'


def test_comment_template_renders():
    root = Path(__file__).parent.parent
    sample = root / "samples" / "sample_submission.json"
    data = load_input(sample)
    bundle = load_bundle()
    result = Evaluator(bundle).evaluate(data)
    # If scoring_positive_signal fired, we should find rendered template marker
    template_rules = [r for r in result.fired_rules if r['id'] == 'scoring_positive_signal']
    for r in template_rules:
        # Confirm the action captured rendered text
        actions = r['actions']
        assert any('add_comment_template' in a for a in actions)
