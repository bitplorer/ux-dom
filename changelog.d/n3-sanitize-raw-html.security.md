- **Security: the last raw string sinks use the HTML allowlist (N3).** A string
  child of a tag with a falsy `escape_string` (`__escape_string=False`, `None`,
  `0`, `""`) was appended verbatim and rendered live; it now goes through
  `defHTML` (safe tags kept, `script` / `on*` / `javascript:` dropped). `Markup`
  and `raw()` stay verbatim; `script` / `style` bodies are unchanged.
  `to_fragment` no longer falls back to `str(obj)`: `bytes` are strict UTF-8
  then sanitized, and any other non-str, non-Markup, non-tag object raises
  `TypeError`. `bytes` children decode as strict UTF-8 (they used to render as
  digits); `bytearray` / `memoryview` children raise `TypeError`.
