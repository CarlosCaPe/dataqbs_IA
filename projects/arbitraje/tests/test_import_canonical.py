import importlib
from pathlib import Path

import pytest


def _repo_root() -> Path:
    # Walk parent directories until we find a repository marker ('.git' or 'pyproject.toml')
    p = Path(__file__).resolve()
    for parent in p.parents:
        # Prefer the workspace root which typically contains both a pyproject.toml and README.md
        if (parent / "pyproject.toml").exists() and (parent / "README.md").exists():
            return parent
    # Fallback: any parent with .git or pyproject
    for parent in p.parents:
        if (parent / ".git").exists() or (parent / "pyproject.toml").exists():
            return parent
    # Fallback: top-most parent
    return p.parents[-1]


def test_canonical_import_resolves_to_canonical_file():
    mod = importlib.import_module("arbitraje.arbitrage_report_ccxt")
    mod_file = Path(getattr(mod, "__file__", None)).resolve()

    # Find canonical file by walking parent candidates (works regardless of which
    # project-level pyproject we detect as root).
    expected = None
    p = Path(__file__).resolve()
    for parent in p.parents:
        cand = (
            parent
            / "projects"
            / "arbitraje"
            / "src"
            / "arbitraje"
            / "arbitrage_report_ccxt.py"
        )
        if cand.exists():
            expected = cand.resolve()
            break

    assert expected is not None, "Could not locate canonical 'arbitrage_report_ccxt.py' in parent candidates"
    assert expected.exists(), f"Canonical file missing: {expected}"
    assert mod_file == expected, f"imported module points to {mod_file}, expected {expected}"


def test_legacy_shim_absent_and_not_importable():
    # Historically there was a nested shim under projects/arbitraje/projects/... which
    # re-exported the canonical implementation. Ensure that shim is absent and not importable.
    shim_path = (
        _repo_root()
        / "projects"
        / "arbitraje"
        / "projects"
        / "arbitraje"
        / "src"
        / "arbitraje"
        / "arbitrage_report_ccxt.py"
    )

    assert not shim_path.exists(), f"Legacy shim still present on disk: {shim_path}"

    with pytest.raises(ModuleNotFoundError):
        importlib.import_module(
            "projects.arbitraje.src.arbitraje.arbitrage_report_ccxt"
        )
