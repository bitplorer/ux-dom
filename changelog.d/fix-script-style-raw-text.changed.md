- **Fix (behaviour change): string children of `script` and `style` are no
  longer HTML-escaped.** They are raw text elements (HTML spec §13.1.2), so
  `script('a < b && c')` used to render `a &lt; b &amp;&amp; c`, which broke the
  JS. It now renders verbatim, also for a `defHTML(..., document=True)` style
  body (string HTML drops `script` in every mode). Other
  elements (including `title`/`textarea`) still escape.
