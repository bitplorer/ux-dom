- **Behaviour: `escape=False` text is escaped.** A raw `<` in text was parsed
  again by the browser (`<&lt;x onfocus` became a live `<ltx onfocus>`). Text
  is escaped on both `escape` settings. Strings are still HTML, not plain text.
- **Behaviour: character references decode like a browser on the HTML-string
  path.** Named references use the case-sensitive HTML5 table (`&AMP;` and
  `&amp;` are `&`) and are escaped again, so a title is kept as written.
  `AT&T` stays `AT&T` (it was `ATT`). Same-line spaces stay, including one
  between inline tags (`<b>a</b> <i>b</i>` was `ab`). Newlines are still
  indentation and drop.
- **Behaviour: unrenderable attribute names are dropped.** `data-a"b`,
  `aria-a'b`, and control characters no longer raise `InvalidAttributeName`
  from untrusted input.
- **Behaviour: `srcdoc` strings are sanitized instead of refused.**
  `<script>` becomes `""`. `<p>harmless</p>` stays. A `__html__` value,
  `Markup` included, is still verbatim.
- **Behaviour: `to_fragment(str)` sanitizes.** A plain string is HTML and uses
  the same allowlist, in fragment mode. Tag trees still render as built.
- **Document mode is a caller keyword.** `defHTML(s, document=True)` /
  `StringToHTML(s, document=True)` keep the doctype, `html` / `head` / `body`,
  `title`, `meta` (no `http-equiv`, or `content-type` / `content-language` /
  `x-ua-compatible`), `link rel=stylesheet|icon` only when `href` is
  same-origin or `https`, and `style` (text verbatim; dropped if it contains
  `<` or sits inside `<svg>` / `<math>`). The input never selects it: a string starting with `<!DOCTYPE` or
  `<html>` is a fragment. Only an author's HTML file returned as a `Path`
  from `Component.render()` opts in.
- **Custom elements need an opt-in.** Unknown tags, custom elements included,
  are unwrapped. `defHTML(s, allow_custom_elements=["x-counter"])` (or
  `["x-*"]`) keeps them with global / `aria-*` / `data-*` attributes. Or use a
  tag tree or `raw()`. See ADR 0002.
- **`escape=False` does not bypass sanitizing.** The parameter is accepted for
  compatibility; string HTML is always sanitized. Trusted HTML uses `raw()` /
  `Markup`.
- **Comments, `noscript`, and `template` content are dropped** from string
  HTML.
