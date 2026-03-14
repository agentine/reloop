"""reloop — Drop-in replacement for nest-asyncio. Allows nested asyncio event loops."""

from reloop._patch import apply, applied, revert

__all__ = ["apply", "revert", "applied"]
