"""Core monkey-patching logic for nested asyncio event loops.

This module monkey-patches asyncio internals. Type checking is largely
disabled because we operate on private attributes and C-level objects.
"""
# mypy: disable-error-code="method-assign,misc,attr-defined,assignment"

from __future__ import annotations

import asyncio
import asyncio.events
import asyncio.tasks
import sys
import threading
from contextlib import contextmanager
from typing import Any, Generator

_lock = threading.Lock()
_patched = False
_originals: dict[str, Any] = {}
# Per-loop stack of current tasks for nesting support
_task_stacks: dict[Any, list[Any]] = {}


def apply() -> None:
    """Patch asyncio to allow nested event loops.

    Safe to call multiple times -- subsequent calls are no-ops.
    Thread-safe.
    """
    global _patched
    with _lock:
        if _patched:
            return
        _save_originals()
        _patch_loop()
        _patch_run()
        _patch_tasks()
        _patched = True


def revert() -> None:
    """Revert all asyncio patches, restoring original behavior.

    Safe to call multiple times -- subsequent calls are no-ops.
    Thread-safe.
    """
    global _patched
    with _lock:
        if not _patched:
            return
        _restore_originals()
        _task_stacks.clear()
        _patched = False


@contextmanager
def applied() -> Generator[None, None, None]:
    """Context manager that patches asyncio on enter and reverts on exit."""
    apply()
    try:
        yield
    finally:
        revert()


def _save_originals() -> None:
    """Save references to original asyncio methods before patching."""
    loop_cls = asyncio.BaseEventLoop
    _originals["run_until_complete"] = loop_cls.run_until_complete
    _originals["run_forever"] = loop_cls.run_forever
    _originals["_run_once"] = loop_cls._run_once
    _originals["asyncio_run"] = asyncio.run
    _originals["Task"] = asyncio.Task
    _originals["_py_enter_task"] = asyncio.tasks._py_enter_task
    _originals["_py_leave_task"] = asyncio.tasks._py_leave_task
    _originals["_enter_task"] = asyncio.tasks._enter_task
    _originals["_leave_task"] = asyncio.tasks._leave_task


def _restore_originals() -> None:
    """Restore original asyncio methods."""
    loop_cls = asyncio.BaseEventLoop
    loop_cls.run_until_complete = _originals["run_until_complete"]
    loop_cls.run_forever = _originals["run_forever"]
    loop_cls._run_once = _originals["_run_once"]
    asyncio.run = _originals["asyncio_run"]
    asyncio.Task = _originals["Task"]
    asyncio.tasks.Task = _originals["Task"]
    asyncio.tasks._py_enter_task = _originals["_py_enter_task"]
    asyncio.tasks._py_leave_task = _originals["_py_leave_task"]
    asyncio.tasks._enter_task = _originals["_enter_task"]
    asyncio.tasks._leave_task = _originals["_leave_task"]
    if hasattr(loop_cls, "_run_nested"):
        del loop_cls._run_nested
    _originals.clear()


def _patch_loop() -> None:
    """Patch event loop methods for re-entrant calls."""
    loop_cls = asyncio.BaseEventLoop

    def run_until_complete(self: Any, future: Any) -> Any:
        self._check_closed()

        new_task = not asyncio.isfuture(future)
        future = asyncio.ensure_future(future, loop=self)
        if new_task:
            future._log_destroy_pending = False

        if not self.is_running():
            return _originals["run_until_complete"](self, future)

        # Re-entrant: step the loop manually until the future completes
        done_event: list[bool] = []

        def on_done(_: Any) -> None:
            done_event.append(True)
            self.stop()

        future.add_done_callback(on_done)
        try:
            self._run_nested()
        except BaseException:
            if new_task and future.done() and not future.cancelled():
                future.exception()  # consume exception
            raise
        finally:
            future.remove_done_callback(on_done)

        if not future.done():
            raise RuntimeError("Event loop stopped before Future completed")
        return future.result()

    def run_forever(self: Any) -> None:
        if not self.is_running():
            _originals["run_forever"](self)
        else:
            self._run_nested()

    def _run_nested(self: Any) -> None:
        """Step the event loop manually for nested invocations."""
        nest_level = getattr(self, "_reloop_nest", 0)
        self._reloop_nest = nest_level + 1
        old_stopping = self._stopping
        self._stopping = False
        try:
            while True:
                self._run_once()
                if self._stopping:
                    break
        finally:
            self._stopping = old_stopping
            self._reloop_nest = nest_level

    def _run_once_patched(self: Any) -> None:
        """Patched _run_once that avoids blocking when in a nested loop."""
        nest_level = getattr(self, "_reloop_nest", 0)
        if nest_level == 0 or not hasattr(self, "_selector"):
            _originals["_run_once"](self)
            return

        # Nested: poll with a short timeout instead of blocking forever
        import heapq

        timeout = 0.0
        if self._scheduled:
            when = self._scheduled[0]._when
            deadline = when - self.time()
            timeout = min(max(0.0, deadline), 0.02)

        event_list = self._selector.select(timeout)
        self._process_events(event_list)

        # Move ready scheduled callbacks
        end_time = self.time() + self._clock_resolution
        while self._scheduled:
            handle = self._scheduled[0]
            if handle._when >= end_time:
                break
            heapq.heappop(self._scheduled)
            handle._scheduled = False
            self._ready.append(handle)

        # Run ready callbacks
        ntodo = len(self._ready)
        for _ in range(ntodo):
            handle = self._ready.popleft()
            if handle._cancelled:
                continue
            handle._run()

    loop_cls.run_until_complete = run_until_complete
    loop_cls.run_forever = run_forever
    loop_cls._run_nested = _run_nested
    loop_cls._run_once = _run_once_patched


def _patch_run() -> None:
    """Patch asyncio.run() to reuse a running loop when inside one."""

    def patched_run(
        main: Any,
        *,
        debug: bool | None = None,
        loop_factory: Any = None,
    ) -> Any:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop is not None and loop.is_running():
            # Inside a running loop -- reuse it
            if debug is not None:
                loop.set_debug(debug)
            return loop.run_until_complete(main)

        # No running loop -- use the original
        kwargs: dict[str, Any] = {}
        if debug is not None:
            kwargs["debug"] = debug
        if sys.version_info >= (3, 12) and loop_factory is not None:
            kwargs["loop_factory"] = loop_factory
        return _originals["asyncio_run"](main, **kwargs)

    asyncio.run = patched_run


def _patch_tasks() -> None:
    """Patch Task to use Python implementation and support nested enter/leave."""
    import _asyncio

    # Use the pure-Python Task so we can intercept _enter_task/_leave_task.
    # The C Task calls _enter_task at the C level, bypassing our patches.
    _PyTask = asyncio.tasks._PyTask
    asyncio.Task = _PyTask
    asyncio.tasks.Task = _PyTask

    # Use _swap_current_task to properly update both C and Python current task state
    _swap = _asyncio._swap_current_task
    _current_tasks = asyncio.tasks._current_tasks

    def _enter_task_nested(loop: Any, task: Any) -> None:
        # Swap at the C level (updates what asyncio.current_task() returns)
        prev = _swap(loop, task)
        if prev is not None:
            if loop not in _task_stacks:
                _task_stacks[loop] = []
            _task_stacks[loop].append(prev)
        # Also update the Python dict for consistency
        _current_tasks[loop] = task

    def _leave_task_nested(loop: Any, task: Any) -> None:
        # Restore previous task from stack, or clear
        if loop in _task_stacks and _task_stacks[loop]:
            prev = _task_stacks[loop].pop()
            if not _task_stacks[loop]:
                del _task_stacks[loop]
        else:
            prev = None
        _swap(loop, prev)
        if prev is not None:
            _current_tasks[loop] = prev
        else:
            _current_tasks.pop(loop, None)

    # Patch the module-level names that _PyTask.__step references
    asyncio.tasks._py_enter_task = _enter_task_nested
    asyncio.tasks._py_leave_task = _leave_task_nested
    # Also patch the public names
    asyncio.tasks._enter_task = _enter_task_nested
    asyncio.tasks._leave_task = _leave_task_nested
