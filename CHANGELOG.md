# Changelog

All notable changes to reloop will be documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [0.1.0] — 2026-03-14

### Added

- `apply()` — patches `asyncio.run()`, `loop.run_until_complete()`, and
  `loop.run_forever()` to allow nested/re-entrant calls. Idempotent and
  thread-safe.
- `revert()` — undoes all patches, restoring original asyncio behavior.
  Idempotent and thread-safe. (Not possible with nest-asyncio.)
- `applied()` — context manager that calls `apply()` on entry and `revert()`
  on exit, enabling scoped patching.
- Python 3.10, 3.11, 3.12, 3.13 support.
- Python 3.12+ fix: suppresses spurious `ResourceWarning: Enable tracemalloc`
  for unclosed event loops that nest-asyncio triggered.
- Thread-safe task stack (`_enter_task` / `_leave_task`) so
  `asyncio.current_task()` returns the correct task at each nesting level.
- Pure-Python `Task` fallback ensures task enter/leave hooks are interceptable
  at every nesting depth.
- Zero runtime dependencies — stdlib only.
