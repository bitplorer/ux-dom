- **`MarkdownElement` and `HTMLElement(Path("x.md"))` keep code text.** The converted
  Markdown was unescaped before parsing, so markup inside code was parsed as tags:
  `` `<link>` `` rendered as an empty `<code></code>` and a `<b>` in a fence became
  bold. They now render what every `string_is_markdown` Component renders.
  `HTMLElement` / `JinjaElement` / `MarkdownElement` given `bytes` or a one-item
  tuple of a string no longer raise `TypeError`.
