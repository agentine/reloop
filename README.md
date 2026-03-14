# reloop

[![CI](https://github.com/agentine/reloop/actions/workflows/ci.yml/badge.svg)](https://github.com/agentine/reloop/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/reloop)](https://pypi.org/project/reloop/)

Drop-in replacement for [nest-asyncio](https://github.com/erdewit/nest_asyncio). Allows nested asyncio event loops.

## Install

```
pip install reloop
```

## Quick Start

```python
import reloop

reloop.apply()
```

That's it. Now `asyncio.run()` and `loop.run_until_complete()` work inside running event loops — Jupyter notebooks, LLM libraries, web framework sync handlers, and anywhere else Python's `RuntimeError: This event loop is already running` gets in your way.

## Usage

```python
import asyncio
import reloop

reloop.apply()

async def inner():
    return 42

async def outer():
    # This would normally raise RuntimeError
    return asyncio.run(inner())

asyncio.run(outer())  # works
```

### Scoped Patching

```python
with reloop.applied():
    asyncio.run(outer())  # patched

asyncio.run(outer())  # raises RuntimeError again
```

### Revert

```python
reloop.apply()
# ... use nested loops ...
reloop.revert()  # restore original asyncio behavior
```

## API

| Function | Description |
|---|---|
| `reloop.apply()` | Patch asyncio to allow nested event loops. Idempotent. Thread-safe. |
| `reloop.revert()` | Undo all patches. Idempotent. Thread-safe. |
| `reloop.applied()` | Context manager: patches on enter, reverts on exit. |

## Migration from nest-asyncio

Search and replace:

```diff
- import nest_asyncio
- nest_asyncio.apply()
+ import reloop
+ reloop.apply()
```

### Differences from nest-asyncio

- **`revert()` support** — nest-asyncio patches are permanent; reloop can undo them
- **Context manager** — `with reloop.applied():` for scoped patching
- **Python 3.12+ fixes** — no `ResourceWarning` for unclosed event loops
- **Thread-safe** — concurrent `apply()` calls are safe
- **Maintained** — nest-asyncio was archived in March 2024

## Compatibility

- Python 3.10+
- Zero dependencies

## License

MIT
