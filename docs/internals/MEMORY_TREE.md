# Tree memory model — lists vs streams

## DOM tree

`children` is a **list** (mutable tree). Building the page holds structure in RAM.

## Serialize

| Mode | How | Peak token buffer |
|------|-----|-------------------|
| **`pretty=False`** (production StreamingResponse) | Pure recursive generator open→children→close | **O(1)** tokens |
| **`pretty=True`** stream | Exact layout engine; each `sb.append` → **bounded queue** (default 256) → yield | **O(queue size)** |
| **`str(node)`** | Joins full string | O(document) |

No `itertools.tee` of the document stream. One layout pass.

```python
# production — true generator
async for tok in root.__async_render__(pretty=False):
    await send(tok)

# pretty stream — exact whitespace, bounded buffer
async for tok in root.__async_render__(pretty=True):
    await send(tok)
```

## Why pretty uses a small queue

The battle-tested layout lives in `_render(sb)` with `sb.append`. Converting
every indent edge case to pure generators risks golden-file drift. A **daemon
worker + `queue.Queue(maxsize=N)`** keeps exact layout while the consumer
pulls tokens under backpressure — one pass, no full-list tee.

Compact mode needs no thread (pure generator).

## Membership

`item in node` uses lazy `_find` (short-circuit). `get()` materializes a list on purpose.


## Pretty stream modes (see PRETTY_STREAM.md)

* Default **`safe`**: same thread as request (CSP-safe).
* Opt-in **`worker`**: bounded queue + timeouts; stamp before stream.
* Production: **`pretty=False`**.
