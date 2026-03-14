"""Tests for thread safety."""

from __future__ import annotations

import asyncio
import threading

import reloop


def _clean() -> None:
    reloop.revert()


class TestThreadSafety:
    def setup_method(self) -> None:
        reloop.revert()

    def teardown_method(self) -> None:
        reloop.revert()

    def test_concurrent_apply(self) -> None:
        """Calling apply() from multiple threads is safe."""
        errors: list[Exception] = []

        def worker() -> None:
            try:
                reloop.apply()
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors

    def test_each_thread_can_run_event_loop(self) -> None:
        """Each thread can run its own event loop after apply()."""
        reloop.apply()

        results: list[int] = []
        errors: list[Exception] = []

        def worker(n: int) -> None:
            try:
                async def coro() -> int:
                    await asyncio.sleep(0.01)
                    return n

                result = asyncio.run(coro())
                results.append(result)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        assert sorted(results) == [0, 1, 2, 3, 4]

    def test_nested_run_in_thread(self) -> None:
        """Nested asyncio.run() works inside a thread."""
        reloop.apply()

        result_box: list[int] = []
        errors: list[Exception] = []

        def worker() -> None:
            try:
                async def inner() -> int:
                    return 7

                async def outer() -> int:
                    return asyncio.run(inner())

                result_box.append(asyncio.run(outer()))
            except Exception as e:
                errors.append(e)

        t = threading.Thread(target=worker)
        t.start()
        t.join()

        assert not errors
        assert result_box == [7]
