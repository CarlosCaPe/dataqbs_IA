from typing import Any

__all__ = ["Swapper"]

def __getattr__(name: str) -> Any:  # PEP 562 lazy attribute access
	if name == "Swapper":
		from .swapper import Swapper
		return Swapper
	raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
