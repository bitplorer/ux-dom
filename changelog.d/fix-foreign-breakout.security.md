- **`style` / `script` after a breakout tag in `<svg>` / `<math>` are raw text
  again.** In foreign content a start tag such as `<p>`, `<div>` or `<img>`
  (and `<font>` with `color` / `face` / `size`) pops the parser back to HTML,
  for its descendants and every later sibling. The renderer now replays that,
  so `svg(div(), script(js))` no longer puts a literal `<![CDATA[` into the
  JS. Where the HTML rules may close an element early, the body stays CDATA
  unless it is raw text in every case. That also covers four shapes that ran
  script, such as `math(mi(p(div(), mglyph(style(...)))))` (#92).
