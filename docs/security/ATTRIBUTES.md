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

**Never spread untrusted keys as attributes.** Name validation only stops a
name from breaking out of the tag. A valid name can still be dangerous on its
own: `onclick`, `@click`, `hx-on:*`, `x-html` and friends run script or
inject HTML by design. Build attribute dicts from keys you choose, and pass
untrusted data only as values.

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


## htmx / SSE / WebSocket URLs

`hx-get`/`hx-post`/… (and `data-hx-*`), `sse-connect`/`ws-connect` (and
`data-*` aliases), `hx-sse`/`hx-ws`, and `data-hx-sse`/`data-hx-ws` accept
**relative same-origin** URLs only. A foreign `https://…` or protocol-relative
`//host/…` is replaced with `about:invalid#ux-dom-unsafe-url`. Opt in explicitly:

```python
from ux_dom.dom import cross_origin, div
div(hx_get=cross_origin("https://api.example.com/feed"))
```

Ordinary `href`/`src` still allow `http`/`https`/… but also refuse `//host`.

### htmx 1.x `connect:<url>`

htmx 1.9.2 reads `hx-sse` / `hx-ws` and the `data-hx-sse` / `data-hx-ws`
spellings (`getAttributeValue` tries `data-` + the name). The value is
whitespace-separated tokens. `connect:<url>` is the network target; `swap:<event>`
and `send:<trigger>` are not URLs.

This parsing applies only to `hx-sse`, `hx-ws`, `data-hx-sse`, and
`data-hx-ws`. On `hx-get` and the other same-origin attributes the whole value
is an ordinary URL, so `hx-get="connect:/feed"` has the scheme `connect` and
is refused.

htmx 1.9.2 splits the attribute on whitespace first (`trim` + `/\s+/`), then
splits each token on the first colon. The same noise strip used for other
URLs runs on each token (HTML-unescape, drop C0 controls, whitespace, and DEL,
then ignore case). Only a token that starts with `connect:` is a URL prefix.
A `:` later in a `swap:` or `send:` name is part of that name (`swap:msg:part`).

| Value | Result |
| --- | --- |
| `connect:/feed`, `connect:/ws`, `CONNECT:/feed`, `connect: /feed` | kept |
| `connect:feed swap:msg` | kept (whitespace separates the tokens) |
| `connect:http://evil`, `connect:https://evil.com/s`, `connect:wss://evil.com/s` | inert URL |
| `connect://evil`, `connect:javascript:…` | inert URL |
| `connect:/feed connect:https://evil.com/s` | inert URL (every leading `connect:` is checked) |
| `https://evil.com/connect:/a`, `//evil.com/connect:/a` | inert URL (the tail does not replace the foreign prefix) |

`cross_origin(...)` opts the URL inside a leading `connect:` into `http` /
`https` / `ws` / `wss`. `cross_origin("connect:javascript:…")`,
`cross_origin("//evil")`, and
`cross_origin("javascript:alert(1)//connect:/a")` stay refused.

**Non-`connect:` tokens.** `swap:<name>` and `send:<name>` stay when `<name>`
contains no `/` or `\`. The name may contain `:`. `swap:https://…`,
`send:wss://…`, and a bare `https://…` are refused. A `connect:` that is not
at the start of a token is not a prefix (`prefixconnect:/feed` is refused).
