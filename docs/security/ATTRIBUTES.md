# Attribute rendering: escaping and unsafe URLs

> **Diátaxis:** reference · **Layer:** ux-dom render path

Every attribute value goes through two steps when the tree renders.

1. **Escape.** `& < > "` are entity-encoded, and C0 control characters are
   stripped, so a value can never close its quotes or open a new tag.
   `div(title='"><img src=x onerror=alert(1)>')` renders one `div` whose
   `title` is that literal text.
2. **Neutralize script URLs (fail closed).** In URL-bearing attributes, a value
   whose scheme is `javascript:`, `vbscript:` or `data:text/html` renders as
   `about:invalid#ux-dom-unsafe-url`, an inert URL in the same style as
   Google Closure's `about:invalid#zClosurez`. Before the scheme check, the
   value is stripped of the whitespace and control characters that browsers
   ignore (`java\tscript:`, a leading `\x01`), and letter case is ignored.

URL-bearing attributes (`ux_dom.dom.src.utils.dom_util.URL_ATTRIBUTES`):
`href`, `src`, `action`, `formaction`, `xlink:href`, `poster`, `cite`,
`background`, `srcdoc`, `data`, `codebase`, `longdesc`, `manifest`, `ping`,
`hx-get`, `hx-post`, `hx-put`, `hx-patch`, `hx-delete`.

Step 2 also applies to attributes marked unescaped (`safe_attributes`), because
no caller needs an executable URL. Safe URLs (`/path`, `https:`, `mailto:`,
`#frag`, `data:image/...`) are untouched.

`safe_attr_value(attribute, value)` is the single implementation. Every
renderer calls it (`dom_tag`, `ext.Tags`, `ext.StyleTags`).

Tests: `tests/07_resilience/test_unsafe_url_attrs.py`,
`tests/07_resilience/test_adversarial_render.py`.
