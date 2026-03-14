# reloop — Drop-in replacement for nest-asyncio

## Overview

**reloop** is a Python library that patches `asyncio` to allow nested event loops. It is a drop-in replacement for `nest-asyncio`, which was archived in March 2024 after its maintainer passed away.

**Replaces:** [nest-asyncio](https://github.com/erdewit/nest_asyncio) (85M downloads/month, archived)

**Package name:** `reloop` (verified available on PyPI)

## Problem

Python's `asyncio` does not allow nested event loops by design. Calling `asyncio.run()` or `loop.run_until_complete()` inside an already-running event loop raises `RuntimeError: This event loop is already running`. This is a blocker in:

- **Jupyter notebooks** — the kernel runs its own event loop
- **LLM libraries** — many call async code synchronously
- **Web frameworks** — sync handlers calling async utilities
- **GUI applications** — event loops already running

CPython issue #22239 was closed as "won't fix", so this need won't be addressed in stdlib.

## Architecture

### Core Module (`reloop.py` or `reloop/__init__.py`)

Single-module library that monkey-patches `asyncio` internals:

1. **`apply()`** — Patches `asyncio.run()`, `loop.run_until_complete()`, `loop.run_forever()`, and related methods to support re-entrant calls.
2. **`revert()`** — Undoes all patches, restoring original asyncio behavior.
3. **Context manager** — `with reloop.applied():` for scoped patching.

### Patching Strategy

- Wrap `run_until_complete()` to detect re-entrant calls and use `_run_once()` stepping instead of blocking
- Wrap `run_forever()` to support nested invocations
- Patch `asyncio.run()` to reuse the running loop when available
- Patch `asyncio.tasks._enter_task` / `_leave_task` for proper task nesting
- Handle `KeyboardInterrupt` propagation correctly

### Key Improvements Over nest-asyncio

1. **Python 3.12+ ResourceWarning fix** — Suppress or properly handle `unclosed event loop` warnings
2. **Python 3.13/3.14 support** — Test and support latest asyncio internals
3. **Revert capability** — `revert()` function to undo patches (nest-asyncio couldn't undo)
4. **Context manager API** — `with reloop.applied():` for scoped use
5. **Thread safety** — Proper handling of concurrent patching
6. **Better error messages** — Clear errors when patching fails

## Deliverables

1. `reloop/` — Python package
   - `__init__.py` — Public API: `apply()`, `revert()`, `applied()` context manager
   - `_patch.py` — Core monkey-patching logic
2. `tests/` — Comprehensive test suite
   - Nested `asyncio.run()` calls
   - Nested `run_until_complete()` calls
   - Task nesting and cancellation
   - `revert()` restores original behavior
   - Thread safety
   - Python 3.10-3.14 compatibility
3. `pyproject.toml` — Modern packaging with hatch/setuptools
4. `README.md` — Usage, migration guide from nest-asyncio
5. `LICENSE` — MIT (matching nest-asyncio)

## Compatibility

- Python 3.10+ (drop legacy Python support)
- Drop-in replacement: `import reloop; reloop.apply()` equivalent to `import nest_asyncio; nest_asyncio.apply()`
- Migration: search-and-replace `nest_asyncio` → `reloop` in most cases

## Scope Boundaries

- Only patch stdlib `asyncio` event loops (matching nest-asyncio behavior)
- uvloop support is a stretch goal, not required for v1.0
- No new async primitives — this is purely about allowing re-entrant loops
