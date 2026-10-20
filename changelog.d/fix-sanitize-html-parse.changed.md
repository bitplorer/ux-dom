- **Behaviour: `escape=False` text is escaped.** A raw `<` in text was parsed
  again by the browser (`<&lt;x onfocus` became a live `<ltx onfocus>`). Text
  is escaped on both `escape` settings. Strings are still HTML, not plain text.
- **Behaviour: character references are re-emitted on the HTML-string path.**
  `&amp;` stays `&amp;` (a title is kept as written). References are not passed
  through `escape()`, which encodes `&`. Same-line spaces stay so the words
  around the reference are not glued together. Newlines are still indentation
  and drop. `AT&T` is unchanged (`ATT`): the parser’s unknown entity name is
  not a character reference this path rewrites.
- **Behaviour: `srcdoc` strings are sanitized instead of refused.**
  `<script>` becomes `""`. `<p>harmless</p>` stays. A non-string `__html__`
  value is still verbatim.
- **Behaviour: `to_fragment(str)` sanitizes.** A plain string is HTML and uses
  the same allowlist, in fragment mode. Tag trees still render as built.
- **Document mode is a caller keyword.** `defHTML(s, document=True)` /
  `StringToHTML(s, document=True)` keep the doctype, `html` / `head` / `body`,
  `title`, `meta` (no `http-equiv`, or `content-type` / `content-language` /
  `x-ua-compatible`), `link rel=stylesheet|icon` only when `href` is
  same-origin or `https`, and `style` (text verbatim; dropped if it contains
  `<`). The input never selects it: a string starting with `<!DOCTYPE` or
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
