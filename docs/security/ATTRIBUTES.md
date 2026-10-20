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
3. **HTML attributes are sanitized.** `srcdoc` holds a whole HTML document, so
   a scheme check means nothing there. A string goes through the same allowlist
   sanitizer as `defHTML` (document mode included). A non-string value that
   implements `__html__` stays verbatim. Either way the renderer still
   attribute-escapes the result.

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

htmx 1.9.2 splits the attribute on JavaScript whitespace first (`trim` +
`/\s+/`), then splits each token on the first colon. That `\s` set is
`[\t\n\v\f\r \u00a0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000\ufeff]`
(U+FEFF included). Python `str.split()` does not split on U+FEFF, so the
gate uses this set. HTML entities are decoded before that split, so
`connect:/f&#32;connect:wss:evil.com` is two tokens and is refused.
Double-encoded entity values are refused. The
same noise strip used for other URLs then runs on each token (drop C0
controls, ASCII whitespace, and DEL, then ignore case). Only a token that
starts with `connect:` is a URL prefix.
A `swap:` or `send:` name must match `[A-Za-z0-9_.-]+`. A colon or any other
character refuses the whole value (`swap:msg:part`). An empty name (`swap:`,
`send:`) and a bare `connect:` are refused.

| Value | Result |
| --- | --- |
| `connect:/feed`, `connect:/ws`, `CONNECT:/feed`, `connect: /feed` | kept |
| `connect:feed swap:msg` | kept (whitespace separates the tokens) |
| `connect:http://evil`, `connect:https://evil.com/s`, `connect:wss://evil.com/s` | inert URL |
| `connect://evil`, `connect:javascript:…` | inert URL |
| `connect:/feed connect:https://evil.com/s` | inert URL (every leading `connect:` is checked) |
| `https://evil.com/connect:/a`, `//evil.com/connect:/a` | inert URL (the tail does not replace the foreign prefix) |
| `swap:x` + U+FEFF + `connect:wss:evil.com` | inert URL (U+FEFF separates the tokens) |
| `swap:msg:part`, `send:`, `connect:` | inert URL |
| `connect:/f&#32;connect:wss:evil.com` | inert URL (the entity is a space, decoded before the split) |

`cross_origin(...)` opts the URL inside a leading `connect:` into `http` /
`https` / `ws` / `wss`. `cross_origin("connect:javascript:…")`,
`cross_origin("//evil")`, and
`cross_origin("javascript:alert(1)//connect:/a")` stay refused.

**Non-`connect:` tokens.** `swap:<name>` and `send:<name>` stay when `<name>`
matches `[A-Za-z0-9_.-]+`. `swap:https://…`, `send:wss://…`, `swap:msg:part`,
and a bare `https://…` are refused. A `connect:` that is not
at the start of a token is not a prefix (`prefixconnect:/feed` is refused).

## String → HTML (`defHTML` / `Fragment(str)`)

One allowlist. `defHTML`, `Fragment(str)`, `Component.render()->str`,
`HTMLElement`, `JinjaElement`, `MarkdownElement`, `to_fragment(str)`, and
`srcdoc` all use it. Strings stay HTML: known-safe tags are kept and
sanitized, they are not turned into plain text. String HTML is always
sanitized: `escape=False` does not bypass the allowlist; the ignored parameter is
pending removal ([ADR 0004](../adr/0004-no-compat-shims-pre-release.md)). Trusted markup uses `raw()` / `Markup` (verbatim). A
`__html__` value is checked before the `str` check, so a `Markup` (a `str`
subclass) passed to `to_fragment`, `srcdoc`, `Fragment`, or returned from
`Component.render()` stays verbatim. A string child added to a tag whose
`escape_string` is falsy (`__escape_string=False`, as on `HTMLElement`) is
HTML and goes through the same allowlist; a `Markup` child stays verbatim.
`bytes` (a child or `to_fragment(bytes)`) are strict UTF-8 first, then the
`str` path; `bytearray` / `memoryview` children and `to_fragment` of any
other object raise `TypeError` (no `str(obj)` fallback). Policy:
[ADR 0002](../adr/0002-html-string-sanitizer-policy.md).

**Tags.** A fragment may contain the known-safe set (the usual content tags,
form controls, `html` / `head` / `body` / `title`, `textarea`, and SVG
geometry such as `svg`, `circle`, `path`). `script`, `iframe`, `object`,
`embed`, `base`, `frame`, `frameset`, `math`, and SVG animation (`animate`,
`set`, `foreignObject`) are dropped with their children. So are the elements a
browser parses as raw text while Python parses their children as markup:
`noscript`, `noembed`, `noframes`, `xmp`, `plaintext`, and `template`. Kept,
`<noscript><!-- </noscript><img onerror=…> --></noscript>` would end early in
a browser and run the `<img>`. Any other tag (`portal`, a custom element) is
removed and its children are kept, so the tag cannot run and the text is not
thrown away. `style`, `meta`, and `link` are not fragment tags.

**Comments** are dropped. A browser ends a comment at `--!>` and in other
places Python does not, so a kept comment can carry live markup.

**Custom elements** are kept only when the caller names them:
`defHTML(s, allow_custom_elements=["x-counter"])` or a `"x-*"` prefix pattern.
A name must be a valid custom element name (lowercase, with `-`, not
reserved), so the opt-in cannot re-allow `script`. A kept custom element gets
the global, `aria-*` and `data-*` attributes only.

**Attributes, per tag.** Global attributes (`class`, `id`, `title`, `lang`,
`dir`, `role`, `style`, `tabindex`, `hidden`, …), `aria-*`, and `data-*`
except `data-hx-*` are kept on an allowed tag. Each tag also has its own
extras (`a` gets `href` / `rel` / `target`, `img` gets `src` / `alt`, `td`
gets `colspan`, …). Anything else is dropped, including every `on*` handler
(`_onclick` included), every `hx-*` and `data-hx-*` attribute, and Alpine
`x-*` / `@*` / `:*`. `srcdoc` is not an allowed attribute on a parsed tag.

**URLs and style.** A URL attribute that stays on the allowlist (`href`,
`src`, `action`, `formaction`, …) still drops `javascript:`, `vbscript:`, and
`data:text/html`. The renderer’s scheme allow-list runs again at serialize
time. `style` drops `expression(`, `javascript:`, and `vbscript:`.

**Text.** Text is escaped whether `escape` is true or false, so a `<` in a
text node cannot be parsed again as a tag. Numeric references are re-emitted
as written (`&#39;`, `&#x61;`). Named references are decoded with the HTML5
table, case-sensitive like a browser (`&AMP;` and `&amp;` are `&`), then
escaped. A name the table does not know is literal text, so `AT&T` stays
`AT&T`. Same-line spaces stay, including a space between inline tags
(`<b>a</b> <i>b</i>`). A newline is source indentation and is still removed.

**Attribute names** that are not `[a-z][a-z0-9_.:-]*` after the leading `_`
is stripped (`data-a"b`, `aria-a'b`, a control character) are dropped, so
untrusted input never reaches the renderer's `InvalidAttributeName`.

**Document mode** is a keyword the caller passes (`defHTML(s,
document=True)`, `StringToHTML(s, document=True)`). The input never selects
it: a string that starts with `<!DOCTYPE` or `<html>` is still a fragment, so
untrusted HTML cannot bring in a stylesheet, a `<style>` (CSS exfiltration) or
a `<meta http-equiv>`. Inside ux-dom only an author's HTML file returned from
`Component.render()` as a `Path` opts in. Also kept in document mode: the
doctype, `title` with its entities as written, `meta` without `http-equiv` or
with `http-equiv` `content-type` / `content-language` / `x-ua-compatible`
(`refresh`, `set-cookie`, `content-security-policy`, … drop the meta), `link`
whose `rel` is only `stylesheet` and/or `icon` and whose `href` is a relative
same-origin URL or `https` (`javascript:` and `http://` links are dropped),
and `style`. `style` text is emitted verbatim (`a > b` stays `a > b`); a
`style` whose text contains `<` is dropped, which covers `</style` in any case.
A `style` inside `<svg>` or `<math>` is always dropped: in foreign content a
browser parses its children as markup and decodes entities. Scripts,
handlers, `hx-*`, and unknown tags are still stripped inside the document.

Tests: `tests/07_resilience/test_html_allowlist.py`,
`tests/07_resilience/test_html_parse_sanitizer.py`,
`tests/07_resilience/test_html_string_mxss.py`.
