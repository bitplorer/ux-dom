# Sync vs async context — one mechanism, two pipelines

## Your situation

You have **two pipelines**:

```text
SYNC:   with tag: ...           →   root.__render__() / str(root)
ASYNC:  async with tag: ...     →   async for t in root.__async_render__()
```

You want **context** (build stack, request nonce, etc.) to stay coherent:

* Sync work must not leak into other threads.
* Async work must not corrupt **other Tasks** on the same thread.
* Serialize must see the same request-scoped vars (CSP nonce) as the handler.

## Answer

**Yes — use `contextvars.ContextVar` for both.**  

You do **not** need two different storage systems. In modern Python:

| Code path | Who owns the Context |
|-----------|----------------------|
| Sync thread | Default / thread Context |
| `asyncio` Task | **Copied Context per Task** |

So:

* **Build stack** (`with` / `async with`) → `ContextVar` (`ux_dom_dom_with_stack`)
* **Request / serialize** (CSP nonce, …) → separate `ContextVar`s on the **same** Context/Task

`__aenter__` / `__aexit__` push the **same** stack as `__enter__` / `__exit__` — isolation comes from the Task’s Context, not from a second dict.

```text
Request Task Context
├── ux_dom_dom_with_stack   ← build (with / async with)
├── ux_dom_csp_nonce        ← serialize (stamp + header)
└── your own ContextVars   ← fine to add
```

## Pairing rules (intent)

| Build | Serialize | Context |
|-------|-----------|---------|
| `with div() as root:` | `str(root)` / `root.__render__()` | Current Context (usually sync thread) |
| `async with div() as root:` | `async for t in root.__async_render__()` | **Same Task’s** Context |
| Sync build then async serialize | OK if you stay on the same Context/Task that holds request vars | |
| Hand off root to another Task | Copy Context (`contextvars.copy_context()`) or re-set needed vars | |

**Do not** put the build stack in a process-global `dict[thread_id]` alone — concurrent Tasks on one worker share a thread and will clobber each other.

## API surface

```python
from ux_dom.dom.src.dom_tag import get_current, context_stack, attr

with div() as root:
    assert get_current() is root
    span("x")

# async
async with div() as root:
    assert get_current() is root
```

CSP (request-scoped):

```python
from ux_dom.plugins.csp import get_nonce  # ContextVar — set by middleware on this Task
```

## What changed

| Before | After |
|--------|--------|
| Global `defaultdict` keyed by `(thread, task, greenlet)` | **`ContextVar` list** for the with-stack |
| Manual task-id in key | Task isolation via asyncio Context copy |
| Easy to forget async vs sync | One stack API; pipelines stay separate only at **serialize** |

## Serialize vs build (again)

Context during **build** attaches children.  
Context during **serialize** (nonce, pretty stream worker) is **request** state.

Pretty stream may use a helper thread for layout: that worker only appends tokens; **do not** rely on ContextVars inside that worker for CSP — stamp the tree **on the request Task** before/during stream start (already the CSP model).

## Tests

* Concurrent `async with` builders — chaos / concurrency suites  
* `tests/test_context_async.py`  
* Pipeline pairing — `tests/test_build_vs_render_pipeline.py`
