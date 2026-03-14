"""Tests for Python version compatibility."""

from __future__ import annotations

import asyncio
import sys
import warnings

import reloop


class TestCompat:
    def setup_method(self) -> None:
        reloop.revert()

    def teardown_method(self) -> None:
        reloop.revert()

    def test_python_version_supported(self) -> None:
        """reloop supports Python 3.10+."""
        assert sys.version_info >= (3, 10)
        reloop.apply()

        async def coro() -> bool:
            return True

        assert asyncio.run(coro()) is True

    def test_no_resource_warning_on_nested(self) -> None:
        """No ResourceWarning for event loops on 3.12+."""
        reloop.apply()

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            async def inner() -> int:
                return 1

            async def outer() -> int:
                return asyncio.run(inner())

            asyncio.run(outer())

            resource_warnings = [
                x for x in w if issubclass(x.category, ResourceWarning)
            ]
            assert len(resource_warnings) == 0, (
                f"Got ResourceWarnings: {resource_warnings}"
            )

    def test_ensure_future_works_nested(self) -> None:
        """asyncio.ensure_future works inside nested loops."""
        reloop.apply()

        async def inner() -> int:
            fut = asyncio.ensure_future(asyncio.sleep(0.01))
            await fut
            return 5

        async def outer() -> int:
            return asyncio.run(inner())

        assert asyncio.run(outer()) == 5

    def test_create_task_in_nested(self) -> None:
        """asyncio.create_task works inside nested loops."""
        reloop.apply()

        async def work() -> int:
            await asyncio.sleep(0.01)
            return 3

        async def inner() -> int:
            task = asyncio.create_task(work())
            return await task

        async def outer() -> int:
            return asyncio.run(inner())

        assert asyncio.run(outer()) == 3
