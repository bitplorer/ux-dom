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
  the same allowlist, including document mode. Tag trees still render as built.
- **Document mode.** A string whose first non-whitespace starts with
  `<!DOCTYPE` or `<html>` keeps the doctype, `html` / `head` / `body`, `title`,
  `meta` (not `http-equiv=refresh`), `link rel=stylesheet|icon` only when
  `href` is same-origin or `https`, and `style`. A fragment still drops
  `style`, `meta`, and `link`. `javascript:` and `http://` links are dropped.
