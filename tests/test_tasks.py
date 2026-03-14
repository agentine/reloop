"""Tests for task nesting and cancellation."""

from __future__ import annotations

import asyncio

import pytest

import reloop


@pytest.fixture(autouse=True)
def _clean_state() -> None:  # type: ignore[misc]
    reloop.revert()
    yield  # type: ignore[misc]
    reloop.revert()


class TestTaskNesting:
    def test_inner_task_from_outer_loop(self) -> None:
        reloop.apply()

        async def inner_task() -> int:
            await asyncio.sleep(0.01)
            return 99

        async def outer() -> int:
            return asyncio.run(inner_task())

        assert asyncio.run(outer()) == 99

    def test_gather_in_nested_loop(self) -> None:
        reloop.apply()

        async def task(n: int) -> int:
            await asyncio.sleep(0.01)
            return n * 2

        async def inner() -> list[int]:
            return list(await asyncio.gather(task(1), task(2), task(3)))

        async def outer() -> list[int]:
            return asyncio.run(inner())

        assert asyncio.run(outer()) == [2, 4, 6]

    def test_current_task_is_correct(self) -> None:
        reloop.apply()

        async def inner() -> asyncio.Task[None] | None:
            return asyncio.current_task()

        async def outer() -> tuple[asyncio.Task[None] | None, asyncio.Task[None] | None]:
            outer_task = asyncio.current_task()
            inner_task = asyncio.run(inner())
            return outer_task, inner_task

        outer_t, inner_t = asyncio.run(outer())
        assert outer_t is not None
        assert inner_t is not None
        assert outer_t is not inner_t


class TestCancellation:
    def test_cancel_in_nested_loop(self) -> None:
        reloop.apply()

        async def cancellable() -> None:
            await asyncio.sleep(10)

        async def outer() -> bool:
            async def run_and_cancel() -> bool:
                task = asyncio.create_task(cancellable())
                await asyncio.sleep(0.05)
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    return True
                return False

            return asyncio.run(run_and_cancel())

        assert asyncio.run(outer()) is True

    def test_timeout_in_nested_loop(self) -> None:
        reloop.apply()

        async def slow() -> None:
            await asyncio.sleep(10)

        async def outer() -> bool:
            async def run_with_timeout() -> bool:
                try:
                    await asyncio.wait_for(slow(), timeout=0.05)
                except asyncio.TimeoutError:
                    return True
                return False

            return asyncio.run(run_with_timeout())

        assert asyncio.run(outer()) is True
