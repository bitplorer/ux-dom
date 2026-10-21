- **Same-name HTML element in an integration point (#128).** In
  `svg(desc(desc(), script(...)))`, `math(mi(mi(), …))` and
  `math(mtext(mtext(), …))` the `script` / `style` rendered as CDATA, a
  SyntaxError in Chromium (never script execution). The namespace model kept a
  state where the inner HTML element was already closed, so its end tag popped
  the integration point. Only elements the HTML parser can close without their
  own end tag (`p`, `li`, `a`, void, table parts …) now keep that state.
