"""Core monkey-patching logic for nested asyncio event loops."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Generator


def apply() -> None:
    """Patch asyncio to allow nested event loops."""


def revert() -> None:
    """Revert all asyncio patches, restoring original behavior."""


@contextmanager
def applied() -> Generator[None, None, None]:
    """Context manager that patches asyncio on enter and reverts on exit."""
    apply()
    try:
        yield
    finally:
        revert()
