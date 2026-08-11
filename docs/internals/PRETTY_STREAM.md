# Pretty streaming — how it is hardened

## One-line rule

**Production HTML streaming uses `pretty=False`.**  
Pretty is for debug/readability. When you do use pretty async stream, **default is safe**.

## Modes

| Mode | How | CSP / ContextVar | Memory | When |
|------|-----|------------------|--------|------|
| **`safe`** (default) | Layout on **request thread**, then yield tokens | Same Context as stamp | ~one full pretty string | Always preferred |
| **`worker`** | Helper thread + bounded queue | **Stamp before** stream; worker must not read nonce | O(queue size) | Huge pretty pages, opt-in |
| **`pretty=False`** | Pure generator | Request Task | O(1) tokens | **Production StreamingResponse** |

Set mode:

```bash
export UI_DOM_PRETTY_STREAM=safe     # default
export UI_DOM_PRETTY_STREAM=worker   # opt-in
```

Or per call:

```python
tree._iter_pretty_stream(0, "  ", True, False, stream_mode="worker")
```

## Why the worker was worrying

CSP nonce lives in a **ContextVar on the request Task**. A helper thread does **not** automatically see that Context.

So:

```text
✅ Request Task: stamp_tree(doc)   # nonce applied to scripts
✅ Then: stream tokens (safe or worker only formats)
❌ Worker must not call get_nonce() / stamp
```

`StreamingResponse` already stamps **before** `__async_render__`.

## Worker hardening (when enabled)

1. **No ContextVar in worker** — only `_render` → `append` → queue  
2. **Bounded queue** + `put_timeout` / `get_timeout` — no infinite hang  
3. **Abandoned consumer** — sets flag so put fails fast  
4. **Exception propagation** from worker to consumer  
5. **Join** on exit; daemon so process exit isn’t blocked forever  
6. **Immutable tree** during stream — don’t mutate nodes while yielding  

## Practical recommendation

```text
HTTP response  →  pretty=False (already default on StreamingResponse)
Debug / logs   →  str(node) or pretty=True with stream_mode=safe
Huge pretty TTFE →  only then consider worker, after stamp
```

## Mental picture

```text
safe (default):
  [request] stamp → layout fully → yield tokens → client

worker (opt-in):
  [request] stamp → start worker
  [worker]  layout append → queue
  [request] yield from queue → client
```

Both keep security stamping on the request side.
