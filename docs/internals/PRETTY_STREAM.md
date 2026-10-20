# Pretty streaming — how it is hardened

## One-line rule

**Production HTML streaming uses `pretty=False`.**  
Pretty is for debug/readability. When you do use pretty async stream, **default is safe**.

## Layout keeps the displayed text

Pretty puts a newline and indent before each child. A browser shows that
newline as a space when it sits between two inline nodes, so those render flat:
text, `<b>`, `<a>`, comments, `{{ var }}`, and every other element in the HTML
spec's phrasing content, plus unknown and custom tags (the safe default).
`<b>a</b><i>b</i>` and `<p>AT&amp;T <b>x</b>.</p>` stay on one line. The inside
edge of an inline element counts too (`<q>` draws quotes there), so `b("x")`
renders `<b>x</b>`.

A newline next to a block-level element (`div`, `p`, `li`, table parts, …)
sits at a line edge, where the browser drops it, so block children keep the
indented layout, with text and inline children between them. Nothing in
`<head>` is displayed, so it stays indented. An element the HTML parser moves
renders flat and counts as inline: `<li>` holding an `<li>`, `<p>` holding a
block, a table part outside its table, inline content directly in a table.

Pretty and flat renders show the same `innerText` in Chromium for a fixed
corpus and 1,200 random trees
(`tests/06_browser/test_pretty_inner_text_browser.py`). A `lazy` child counts
as inline, since its result is unknown until it renders. The whole subtree
under a flat parent is flat. CSS can change `display` (a `class="block"` span,
an `inline` div); the layout follows the browser's default stylesheet. The
check is memoized per render, so it stays linear in the tree size.

The body of a raw text or preformatted element (`script`, `style`,
`textarea`, `title`, `xmp`, `iframe`, `noembed`, `noframes`, `noscript`,
`plaintext`, `pre`, `listing`) is written exactly as the flat render writes
it, with no added newline or indent: there whitespace is a JS template
literal, a CSS string, a form value or preformatted text. The element is
matched by the name its start tag writes, as the parser matches it, and the
subtree below it is flat. Inside `<svg>` / `<math>` the CDATA body of
`script` / `style` is the same as flat too. Only the layout around the
element is pretty (`tests/06_browser/test_pretty_raw_text_browser.py`).

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
