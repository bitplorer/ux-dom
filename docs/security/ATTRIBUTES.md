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
because no caller needs an executable URL. An unescaped attribute still has
`&` and `"` escaped (`escape_attr_minimal`), so it can never close its quotes;
only `'`, `<` and `>` stay literal, for Alpine JSON and handlers. This
opt-out path is **HTML-only**: under XHTML/XML serialization a raw `<` in an
attribute value is not well-formed, so do not opt attributes out when you
render XHTML. The
`safe_attributes` map is per tag instance; marking one tag never changes
another.

**Attribute names are validated.** On every render path (`dom_tag`,
`ext.Tags`, `ext.StyleTags`), a name containing whitespace, `"`, `'`, `>`,
`/`, `=` or a control character, or an empty name, raises
`InvalidAttributeName` (a `ValueError`) instead of rendering. Without this,
`span(**{'x" onmouseover="alert(1)': "1"})` would inject an event handler.
Alpine and htmx names (`@click`, `:class`, `x-on:keyup.enter`, `hx-post`)
are valid.

The checked text is what renders: `safe_attr_value` calls `str(value)` (or
`__html__()`) once and returns that string, so an object cannot return a safe
string to the check and a different one to the renderer.

**Behaviour change: refused schemes.** Because this is an allow-list, every
scheme not listed above is refused, including ones that were allowed before:
`ftp:`, `sms:`, `file:`, `blob:`, `geo:`, `webcal:`, `data:image/svg+xml` and
`data:text/plain`. Link to them through an `https:` URL instead.

**Open-redirect note.** Scheme-relative URLs (`//host/x`), and the browser
variants `\\host` and `/\host`, count as relative and pass. They are not XSS,
but they can point off-site: never build a redirect or link target from
untrusted input without checking the host yourself.

Out of scope: Alpine bindings such as `:href` / `x-bind:href` hold JavaScript
expressions, not URLs; never put untrusted text in them.

`safe_attr_value(attribute, value)` is the single implementation. Every
renderer calls it (`dom_tag`, `ext.Tags`, `ext.StyleTags`).

Tests: `tests/07_resilience/test_unsafe_url_attrs.py`,
`tests/07_resilience/test_adversarial_render.py`.
