# Attribute rendering: escaping and unsafe URLs

> **Diátaxis:** reference · **Layer:** ux-dom render path

Every attribute value goes through two steps when the tree renders.

1. **Escape.** `& < > "` are entity-encoded, and C0 control characters are
   stripped, so a value can never close its quotes or open a new tag.
   `div(title='"><img src=x onerror=alert(1)>')` renders one `div` whose
   `title` is that literal text.
2. **Allow-list URLs (fail closed).** In URL-bearing attributes only these
   values pass: relative URLs (`/a`, `a/b`, `?q`, `#f`, `//host/x`), the
   schemes `http:`, `https:`, `mailto:`, `tel:`, and
   `data:image/{png,jpeg,gif,webp}` (never `image/svg+xml`, which can run
   script). Anything else renders as `about:invalid#ux-dom-unsafe-url`, an
   inert URL in the style of Google Closure's `about:invalid#zClosurez`.
   The check runs on `str(value)` (so non-`str` values cannot slip past),
   after HTML entities are decoded (`&#106;avascript:`, `javascript&colon;`)
   and after the whitespace and C0 controls browsers ignore in a scheme are
   removed (`java\tscript:`). Letter case is ignored.
3. **HTML attributes are refused.** `srcdoc` holds a whole HTML document, so a
   scheme check means nothing there. It renders as the inert URL unless the
   value explicitly opts in through the `__html__` protocol (for example
   MarkupSafe's `Markup`); the opted-in HTML is still attribute-escaped.

URL-bearing attributes (`ux_dom.dom.src.utils.dom_util.URL_ATTRIBUTES`):
`href`, `src`, `action`, `formaction`, `xlink:href`, `poster`, `cite`,
`background`, `data`, `codebase`, `longdesc`, `manifest`, `ping`, `icon`,
`archive`, `usemap`, `profile`, `lowsrc`, `dynsrc`, `hx-get`, `hx-post`,
`hx-put`, `hx-patch`, `hx-delete`. HTML attributes (`HTML_ATTRIBUTES`):
`srcdoc`.

Steps 2 and 3 also apply to attributes marked unescaped (`safe_attributes`),
because no caller needs an executable URL.

Out of scope: Alpine bindings such as `:href` / `x-bind:href` hold JavaScript
expressions, not URLs; never put untrusted text in them.

`safe_attr_value(attribute, value)` is the single implementation. Every
renderer calls it (`dom_tag`, `ext.Tags`, `ext.StyleTags`).

Tests: `tests/07_resilience/test_unsafe_url_attrs.py`,
`tests/07_resilience/test_adversarial_render.py`.
