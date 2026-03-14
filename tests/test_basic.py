"""Basic tests for apply/revert/applied and nested event loops."""

from __future__ import annotations

import asyncio

import pytest

import reloop


@pytest.fixture(autouse=True)
def _clean_state() -> None:  # type: ignore[misc]
    """Ensure each test starts with a clean (unpatched) state."""
    reloop.revert()
    yield  # type: ignore[misc]
    reloop.revert()


class TestApplyRevert:
    def test_apply_allows_nested_run(self) -> None:
        reloop.apply()

        async def inner() -> int:
            return 42

        async def outer() -> int:
            return asyncio.run(inner())

        assert asyncio.run(outer()) == 42

    def test_apply_is_idempotent(self) -> None:
        reloop.apply()
        reloop.apply()  # should not raise

        async def inner() -> int:
            return 1

        async def outer() -> int:
            return asyncio.run(inner())

        assert asyncio.run(outer()) == 1

    def test_revert_restores_original_behavior(self) -> None:
        reloop.apply()
        reloop.revert()

        async def inner() -> int:
            return 1

        async def outer() -> int:
            return asyncio.run(inner())

        with pytest.raises(RuntimeError, match="running"):
            asyncio.run(outer())

    def test_revert_is_idempotent(self) -> None:
        reloop.apply()
        reloop.revert()
        reloop.revert()  # should not raise

    def test_applied_context_manager(self) -> None:
        async def inner() -> str:
            return "ctx"

        async def outer() -> str:
            return asyncio.run(inner())

        with reloop.applied():
            assert asyncio.run(outer()) == "ctx"

        # After exiting, nesting should fail again
        with pytest.raises(RuntimeError, match="running"):
            asyncio.run(outer())


class TestNestedRunUntilComplete:
    def test_nested_run_until_complete(self) -> None:
        reloop.apply()

        async def inner() -> str:
            await asyncio.sleep(0.01)
            return "hello"

        async def outer() -> str:
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(inner())

        assert asyncio.run(outer()) == "hello"

    def test_triple_nesting(self) -> None:
        reloop.apply()

        async def deep() -> str:
            return "deep"

        async def mid() -> str:
            return asyncio.run(deep())

        async def top() -> str:
            return asyncio.run(mid())

        assert asyncio.run(top()) == "deep"

    def test_nested_with_await(self) -> None:
        reloop.apply()

        async def inner() -> int:
            await asyncio.sleep(0.01)
            return 10

        async def outer() -> int:
            a = await asyncio.sleep(0.01) or 0
            b = asyncio.run(inner())
            return a + b

        assert asyncio.run(outer()) == 10

    def test_nested_exception_propagates(self) -> None:
        reloop.apply()

        async def failing() -> None:
            raise ValueError("test error")

        async def outer() -> None:
            asyncio.run(failing())

        with pytest.raises(ValueError, match="test error"):
            asyncio.run(outer())
