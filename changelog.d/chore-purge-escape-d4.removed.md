- **`escape=` on string HTML:** `defHTML`, `StringToHTML` and `_sanitized_html` no
  longer take `escape` (it was ignored; string HTML is always sanitized, ADR 0002).
  `defHTML(s, escape=False)` raises `TypeError`: drop the argument.
- **`escape_string` / `__escape_string=`:** removed from tags and `Component`. A string
  child of a tag is text; add a string as HTML with `tag(*defHTML(s))` (or
  `tag.add(*defHTML(s))`), and trusted markup with `raw()`. `HTMLElement`,
  `JinjaElement` and `MarkdownElement` parse each string in the list, tuple or
  generator they are given, as before; only `add()` after construction changes
  (a string is now text there too).
