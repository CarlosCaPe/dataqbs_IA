from pathlib import Path
import json
from copy import deepcopy
from oai_code_evaluator.cli import load_input
from oai_code_evaluator.config_loader import load_config_dir, validate_bundle
from oai_code_evaluator.evaluator import Evaluator


def load_base():
    root = Path(__file__).parent.parent
    sample = root / "samples" / "sample_submission.json"
    data = load_input(sample)
    bundle = validate_bundle(load_config_dir(root / "config_samples"))
    return data, bundle


def test_dimension_gt_lt():
    data, bundle = load_base()
    # Force a low optimality to trigger penalize_low_optimality rule
    data.submission.ratings.optimality = 2.0  # type: ignore[attr-defined]
    result = Evaluator(bundle).evaluate(data)
    fired_ids = {r['id'] for r in result.fired_rules}
    assert 'penalize_low_optimality' in fired_ids


def test_comment_dedupe_and_stop_after_first():
    data, bundle = load_base()
    # Duplicate a keyword to increase chance of multiple rules; adjust bundle options
    rules_conf = deepcopy(bundle['rules'])
    rules_conf.setdefault('options', {})
    rules_conf['options']['stop_after_first'] = True
    bundle['rules'] = rules_conf
    result = Evaluator(bundle).evaluate(data)
    # If stop_after_first true, at most 1 rating rule should fire
    rating_ids = [r['id'] for r in result.fired_rules if r['type'] == 'rating']
    assert len(rating_ids) <= 1
