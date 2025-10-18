"""Test/run helper: ensure src/ is importable as a package root.

This is picked up automatically by Python if present on sys.path.
"""

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
_SRC = _ROOT / "src"
if _SRC.exists() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))
