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
