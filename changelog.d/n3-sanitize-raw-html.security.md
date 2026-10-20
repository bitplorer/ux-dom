- **Security: the last raw string sinks use the HTML allowlist (N3).** A string
  child of a tag with a falsy `escape_string` (`__escape_string=False`, `None`,
  `0`, `""`) was appended verbatim and rendered live; it now goes through
  `defHTML` (safe tags kept, `script` / `on*` / `javascript:` dropped). `Markup`
  and `raw()` stay verbatim; `script` / `style` bodies are unchanged.
  `to_fragment` no longer falls back to `str(obj)`: `bytes` are strict UTF-8
  then sanitized, and any other non-str, non-Markup, non-tag object raises
  `TypeError`. `bytes` children decode as strict UTF-8 (they used to render as
  digits); `bytearray` / `memoryview` children raise `TypeError`.
- **Security: `tag[i] = value` and `lazy()` no longer emit raw strings.**
  Setting a child by index takes the same path as `add()` (escaped, or
  sanitized under a falsy `escape_string`; `raw()` / tags unchanged). A
  `lazy()` result that is not a tag, `raw()` or `Markup` is escaped as text
  (verbatim inside `script` / `style`). `to_fragment` accepts any object with
  `__render__`.
- **Security: `tag[i] = [..]`, `dom_string`, and `open_tag` / `close_tag`.**
  A list or tuple set by index adds each element through `add()` (it used to
  render as raw `str(list)`); a `dom_string` is escaped like `add()` escapes
  it; `None`, `bool` and `dict` raise `TypeError`. `open_tag` / `close_tag`
  replace the tag verbatim, so they must be `markupsafe.Markup` (the Jinja
  template tags build theirs that way); a plain string raises `TypeError` at
  render.
- **Security: tag names are validated where they are emitted.** A `tagname`
  from a kwarg, a dict child, `tag["tagname"]`, an instance or class
  attribute, or `create_dynamic_element` must match
  `[A-Za-z][A-Za-z0-9._:-]*` (HTML, camelCase SVG, `svg:rect`, custom
  elements); otherwise rendering (or creating the dynamic element) raises
  `InvalidTagName` (a `ValueError`). `div(tagname="img src=x onerror=…")`
  used to inject an element.
