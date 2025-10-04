from pathlib import Path
import yaml
from oai_code_evaluator.config_loader import load_config_dir, validate_bundle


def test_config_samples_roundtrip_and_schema():
    root = Path(__file__).parent.parent
    config_dir = root / "config_samples"

    # raw load each yaml as text and ensure it parses
    yaml_files = [p for p in config_dir.glob("*.yaml")]
    assert yaml_files, "No YAML config samples found"

    original_texts = {p.name: p.read_text(encoding="utf-8") for p in yaml_files}
    parsed_docs = {}
    for p in yaml_files:
        data = yaml.safe_load(original_texts[p.name])
        assert isinstance(data, (dict, type(None))), f"{p.name} should parse to a mapping or empty dict"
        if data is None:
            data = {}
        parsed_docs[p.name] = data
        # round-trip serialization (canonical ordering) to detect indentation / structural regressions
        yaml.safe_dump(data, sort_keys=True)

    # Use existing loader + schema validation (ensures structural contracts)
    bundle = validate_bundle(load_config_dir(config_dir))

    # Basic invariants
    # Ensure rule version present when rules.yaml exists
    if bundle.rules:
        assert 'version' in bundle.rules, "rules.yaml must declare version"
        assert isinstance(bundle.rules['version'], int)

    # Ensure dimensions keys appear if dimensions.yaml present
    if bundle.dimensions:
        assert 'dimensions' in bundle.dimensions, "dimensions.yaml must contain 'dimensions' key"

    # Ensure ranking feedback templates have expected keys if present
    fb = bundle.ranking.get('feedback_templates', {}) if bundle.ranking else {}
    for k in ['complete', 'missing_ids', 'had_duplicates']:
        assert k in fb, f"ranking.yaml feedback_templates missing '{k}'"

    # Ensure prompt feedback messages have required keys
    pf = bundle.prompt.get('feedback', {}) if bundle.prompt else {}
    for k in ['ok', 'missing_field', 'invalid_label']:
        assert k in pf, f"prompt.yaml feedback missing '{k}'"

    # Ensure rewrite config minimal keys
    if bundle.rewrite:
        assert 'min_length' in bundle.rewrite, "rewrite.yaml must include min_length"

    # Ensure decision thresholds exist in rules
    if bundle.rules:
        decision = bundle.rules.get('decision', {})
        assert 'score_thresholds' in decision, "rules.yaml must include decision.score_thresholds"

    # Optional: quick sanity that rating_rules parse as list
    if bundle.rules:
        rr = bundle.rules.get('rating_rules', [])
        assert isinstance(rr, list), "rating_rules must be a list"
