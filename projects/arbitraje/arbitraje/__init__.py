"""Editable package shim for running `python -m arbitraje.*` without install.

This lets subprocess CLI tests import `arbitraje` while we develop from source.
It simply adds the sibling `src` directory to sys.path when needed.
"""

from __future__ import annotations
import sys
from pathlib import Path

_PKG_ROOT = Path(__file__).resolve().parents[1]
_SRC = _PKG_ROOT / "src"
if _SRC.exists():
    s = str(_SRC)
    if s not in sys.path:
        sys.path.insert(0, s)
    # Extend this package's search path to include the real source package dir
    try:
        __path__.insert(0, str(_SRC / "arbitraje"))  # type: ignore[name-defined]
    except Exception:
        pass

# Optionally expose version if available in the real package
try:
    from arbitraje import __version__  # type: ignore  # noqa: F401
except Exception:
    pass
