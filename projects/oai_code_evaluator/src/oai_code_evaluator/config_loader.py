from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import yaml
from jsonschema import ValidationError, validate

from .schemas import SCHEMAS

CONFIG_FILENAMES = [
    "dimensions.yaml",
    "ranking.yaml",
    "prompt.yaml",
    "rewrite.yaml",
    "rules.yaml",
]


class ConfigBundle(dict):
    """Simple dict subclass for dot-access convenience (optional)."""

    def __getattr__(self, item):  # pragma: no cover (syntactic sugar)
        try:
            return self[item]
        except KeyError as e:  # noqa: B904
            raise AttributeError(item) from e


def load_yaml(path: Path) -> Dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if data is None:
        data = {}
    if not isinstance(data, dict):
        raise ValueError(f"File {path.name} must contain a YAML object (mapping).")
    return data


def load_config_dir(config_dir: Path) -> ConfigBundle:
    bundle: Dict[str, Any] = {}
    for name in CONFIG_FILENAMES:
        file_path = config_dir / name
        if file_path.exists():
            bundle[name.split(".")[0]] = load_yaml(file_path)
        else:
            bundle[name.split(".")[0]] = {}
    return ConfigBundle(bundle)


def validate_dimensions(dim_conf: Dict[str, Any]):
    dims = dim_conf.get("dimensions", {})
    for dim, spec in dims.items():
        for key in ["ideal", "tolerance"]:
            if key not in spec:
                raise ValueError(f"Dimension '{dim}' missing required key '{key}' in dimensions.yaml")


def validate_bundle(bundle: ConfigBundle):
    # Validate with jsonschema where available
    for key, schema in SCHEMAS.items():
        data = bundle.get(key, {})
        try:
            validate(instance=data, schema=schema)
        except ValidationError as e:
            raise ValueError(f"Schema error in '{key}': {e.message}") from e
    return bundle
