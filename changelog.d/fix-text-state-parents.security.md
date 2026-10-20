- **Security: nothing below `textarea`, `title`, `xmp`, `iframe`, `noembed`,
  `noframes` or `noscript` can end it early.** The parser reads their body as
  text up to their own end tag, so `textarea(style("</textarea><img src=x
  onerror=alert(1)>"))` ran. Each now checks its joined body for `</name`:
  `textarea` / `title` write it as `&lt;/name` (same value), the RAWTEXT
  elements raise `InvalidNodeContext`. Text renders byte-identically (#90).
