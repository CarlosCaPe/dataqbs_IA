"""Deprecated entrypoints / helpers.

Provides a legacy console-script compatible function that warns users
about the rename telus->tls.
"""
from __future__ import annotations
import sys
from .runner import main as _main

def legacy_entrypoint():  # pragma: no cover - thin shim
    print("[DEPRECATED] 'telus-compare' ha sido renombrado a 'tls-compare-images'.", file=sys.stderr)
    return _main()
