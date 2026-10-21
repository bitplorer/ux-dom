# Attribute rendering: escaping and unsafe URLs

> **Diátaxis:** reference · **Layer:** ux-dom render path


Every attribute value goes through these steps when the tree renders.

1. **Escape.** `& < > "` are entity-encoded, and C0 control characters are
   stripped, so a value can never close its quotes or open a new tag.
   `div(title='"><img src=x onerror=alert(1)>')` renders one `div` whose
   `title` is that literal text.
2. **Allow-list URLs (fail closed).** In URL-bearing attributes only these
   values pass: relative URLs (`/a`, `a/b`, `?q`, `#f`), the schemes
   `http:`, `https:`, `mailto:`, `tel:` and `sms:`, and
   `data:image/{png,jpeg,jpg,gif,webp,avif}` (never `image/svg+xml`, which
   can run script). Scheme-relative URLs (`//host/x`, `\\host`, `/\host`)
   are refused: they point at another origin. Anything else renders as
   `about:invalid#ux-dom-unsafe-url`, an inert URL in the style of Google
   Closure's `about:invalid#zClosurez`. The check runs on the text that
   renders: `str(value)` for any type (`Markup`, numbers, `lazy`, objects
   with `__str__` or `__html__`), or the JSON text of a list or dict value
   (SMIL splits that text on `;` too). It runs after HTML
   entities are decoded (`&#106;avascript:`, `javascript&colon;`) and after
   the whitespace and C0 controls browsers ignore in a scheme are removed
   (`java\tscript:`). Letter case is ignored.
3. **Lists of URLs.** In `srcset` and `imagesrcset`, each image candidate's
   URL gets the check of step 2. Candidates are split as the HTML spec's
   srcset parser splits them, so a comma inside a `data:` URL stays part of
   it. If any candidate fails, the whole value becomes the inert URL.
4. **SVG animation values.** `animate`, `set`, `animateMotion` and
   `animateTransform` can set any attribute, `href` included, so
   `<animate attributeName="href" to="javascript:…">` would run script on
   click ([#86](https://github.com/bitplorer/ux-dom/issues/86)). On these
   elements `to`, `from`, `by` and each `;`-separated item of `values` get
   the check of step 2, whatever `attributeName` says. Ordinary values
   (`0;1`, `rgb(0, 128, 0)`, `10px`, `#id`) have no scheme and pass as
   relative URLs.
5. **HTML attributes are sanitized.** `srcdoc` holds a whole HTML document, so
   a scheme check means nothing there. A string goes through the same allowlist
   sanitizer as `defHTML` (document mode included). A non-string value that
   implements `__html__` stays verbatim. Either way the renderer still
   attribute-escapes the result.

The sets, as `ux_dom.dom.src.utils.dom_util` defines them
(`tests/04_production/test_attribute_docs_match_code.py` keeps this table
equal to the code):

| Set | Members |
| --- | --- |
| `URL_ATTRIBUTES` | `action`, `archive`, `background`, `cite`, `codebase`, `data`, `dynsrc`, `formaction`, `href`, `icon`, `longdesc`, `lowsrc`, `manifest`, `ping`, `poster`, `profile`, `src`, `usemap`, `xlink:href` |
| `_SRCSET_ATTRIBUTES` | `imagesrcset`, `srcset` |
| `_ANIMATION_TAGS` | `animate`, `animateMotion`, `animateTransform`, `set` |
| `_ANIMATION_VALUE_ATTRIBUTES` | `by`, `from`, `to`, `values` |
| `_SAFE_SCHEMES` | `http`, `https`, `mailto`, `sms`, `tel` |
| `_SAFE_DATA_IMAGE_TYPES` | `avif`, `gif`, `jpeg`, `jpg`, `png`, `webp` |
| `SAME_ORIGIN_URL_ATTRIBUTES` | `data-hx-delete`, `data-hx-get`, `data-hx-patch`, `data-hx-post`, `data-hx-put`, `data-hx-sse`, `data-hx-ws`, `data-sse-connect`, `data-ws-connect`, `hx-delete`, `hx-get`, `hx-patch`, `hx-post`, `hx-put`, `hx-sse`, `hx-ws`, `sse-connect`, `ws-connect` |
| `HTML_ATTRIBUTES` | `srcdoc` |
| `BOOLEAN_ATTRIBUTES` | `allowfullscreen`, `alpha`, `async`, `autofocus`, `autoplay`, `checked`, `controls`, `default`, `defer`, `disabled`, `formnovalidate`, `headingreset`, `inert`, `ismap`, `itemscope`, `loop`, `multiple`, `muted`, `nomodule`, `novalidate`, `open`, `playsinline`, `readonly`, `required`, `reversed`, `selected`, `shadowrootclonable`, `shadowrootcustomelementregistry`, `shadowrootdelegatesfocus`, `shadowrootserializable` |

`SAME_ORIGIN_URL_ATTRIBUTES` follow the stricter rule in
[htmx / SSE / WebSocket URLs](#htmx--sse--websocket-urls).

`meta content` is not checked. A refresh URL there (`0;url=javascript:…`,
`data:text/html`) did not run in Chromium, and `content` on other `meta`
elements is free text.

Steps 2 to 5 also apply to attributes marked unescaped (`safe_attributes`),
because no caller needs an executable URL. An unescaped attribute still has
`&` and `"` escaped (`escape_attr_minimal`), so it can never close its quotes;
only `'`, `<` and `>` stay literal, for Alpine JSON and handlers. ux-dom
renders HTML only; there is no XHTML mode (#87). The
`safe_attributes` map is per tag instance; marking one tag never changes
another.

**Attribute names are validated.** On every render path (`dom_tag`,
`ext.Tags`, `ext.StyleTags`), a name containing whitespace, `"`, `'`, `>`,
`/`, `=` or a control character, or an empty name, raises
`InvalidAttributeName` (a `ValueError`) instead of rendering. Without this,
`span(**{'x" onmouseover="alert(1)': "1"})` would inject an event handler.
Alpine and htmx names (`@click`, `:class`, `x-on:keyup.enter`, `hx-post`)
are valid.

**Boolean attributes take `True`, `False` or `None`.** For the HTML boolean
attributes (`BOOLEAN_ATTRIBUTES`, the WHATWG attribute index's "Boolean
attribute" entries), `True` renders `name="name"`, `False` and `None` omit the
attribute, and any other value raises `TypeError`. A browser treats any value
as present, so `checked="unchecked"` or `disabled="false"` would turn the state
on ([#122](https://github.com/bitplorer/ux-dom/issues/122)). The rule holds for
keyword arguments, `tag["checked"] = …` and `attr(...)`, and names match in any
case. Parsed HTML keeps a boolean attribute as `True`, whatever its value, as
a browser does. Only these names are governed: attributes that look boolean
but are enumerated or belong to htmx / Alpine (`hidden="until-found"`,
`draggable="false"`, `hx-boost="false"`, `x-cloak`) keep their values, and SVG
tags are not governed. Browser check:
`tests/06_browser/test_boolean_state_browser.py`.

**Never spread untrusted keys as attributes.** Name validation only stops a
name from breaking out of the tag. A valid name can still be dangerous on its
own: `onclick`, `@click`, `hx-on:*`, `x-html` and friends run script or
inject HTML by design. Build attribute dicts from keys you choose, and pass
untrusted data only as values.

The checked text is what renders: `safe_attr_value` calls `str(value)` (or
`__html__()`) once and returns that string, so an object cannot return a safe
string to the check and a different one to the renderer. A list or dict value
is dumped to JSON first, and the JSON text is what gets checked.

**Refused schemes.** Because this is an allow-list, every scheme not listed
above is refused, including `ftp:`, `file:`, `blob:`, `geo:`, `webcal:`,
custom schemes (`web+app:`), `data:image/svg+xml` and `data:text/plain`. Link
to them through an `https:` URL instead. There is no per-value opt-in yet: a
typed `SafeURL` is planned only when a real caller needs one
([ADR 0002, amendment](../adr/0002-html-string-sanitizer-policy.md#amendment-url-values-from-python-86)).

**Open-redirect note.** `https://` URLs to any host pass. They are not XSS,
but they can point off-site: never build a redirect or link target from
untrusted input without checking the host yourself.

Out of scope: Alpine bindings such as `:href` / `x-bind:href` hold JavaScript
expressions, not URLs; never put untrusted text in them.

`safe_attr_value(attribute, value, tag="")` is the single implementation.
Every renderer calls it (`dom_tag`, `ext.Tags`, `ext.StyleTags`); the HTML
renderers pass the element name as `tag` for the animation rule (step 4).

Tests: `tests/07_resilience/test_unsafe_url_attrs.py`,
`tests/07_resilience/test_svg_animation_urls.py`,
`tests/07_resilience/test_adversarial_render.py`; Chromium oracle:
`tests/06_browser/test_svg_animation_url_browser.py`.


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
`HTMLElement`, `JinjaElement`, `MarkdownElement`, `to_fragment(str)`,
`srcdoc`, and `ux_dom.response.sanitize_html` / `sanitize_html_stream` all
use it. A stream gives the same bytes as the whole string wherever its chunks
are split; it is cut only where the tokenizer has nothing open (#121). Strings stay HTML: known-safe tags are kept and
sanitized, they are not turned into plain text. String HTML is always
sanitized and has no `escape` parameter. Trusted markup uses `raw()` /
`Markup` (verbatim). A `__html__` value is checked before the `str` check, so
a `Markup` (a `str` subclass) passed to `to_fragment`, `srcdoc`, `Fragment`,
or returned from `Component.render()` stays verbatim. A string child added to
a tag is text; to add a string as HTML, add `*defHTML(s)`. `HTMLElement`,
`JinjaElement` and `MarkdownElement` do that for each string in the list,
tuple or generator they are given (a `Markup` stays verbatim).
`bytes` (a child or `to_fragment(bytes)`) are strict UTF-8 first, then the
`str` path; `bytearray` / `memoryview` children and `to_fragment` of any
other object without `__render__` raise `TypeError` (no `str(obj)`
fallback). `tag[i] = value` follows the same rules as `add()` (a list or
tuple adds each element; a `dom_string` is escaped; `None` / `bool` / `dict`
raise `TypeError`). The `open_tag` / `close_tag` controls replace the tag
verbatim, so they accept only `Markup`; a plain string raises `TypeError`. A
`lazy()` result is escaped as text unless it is a tag, `raw()`, or `Markup`.
`raw()` is the explicit verbatim opt-out. The element name comes only from
an instance or class `tagname` (`dom_tag._tagname()`), never from the
attribute dict, so `div(tagname=…)` is an ordinary attribute. Tag names are
checked at render
(`checked_tag_name`, `[A-Za-z][A-Za-z0-9._:-]*`) wherever they come from;
a bad name raises `InvalidTagName` (`ValueError`). A name containing `-`
must instead be a valid custom element name (`[a-z] PCENChar* - PCENChar*`,
non-ASCII allowed). `comment()` text and `DocType()` text are checked
against the HTML spec's comment and doctype grammar; a breakout raises
`InvalidMarkupToken` (`ValueError`). Jinja DSL arguments (`Var`, `For`, …)
are template source, trusted like `raw()`. Policy:
[ADR 0002](../adr/0002-html-string-sanitizer-policy.md).

**Tags.** A fragment may contain the known-safe set (the usual content tags,
form controls, `html` / `head` / `body` / `title`, `textarea`, and SVG
geometry and paint such as `svg`, `circle`, `path`, `linearGradient`,
`radialGradient`, `clipPath`, `textPath`). Tag names are matched in any case
and a kept camelCase SVG name is written with its case, from the HTML
parser's SVG tag-name table. `script`, `iframe`, `object`, `embed`, `base`,
`frame`, `frameset`, `math`, SVG animation (`animate`, `animateMotion`,
`animateTransform`, `set`) and `foreignObject` are dropped with their
children. SVG filters, `image` and `feImage` are unwrapped. So are the elements a
browser parses as raw text while Python parses their children as markup:
`noscript`, `noembed`, `noframes`, `xmp`, `plaintext`, and `template`. Kept,
`<noscript><!-- </noscript><img onerror=…> --></noscript>` would end early in
a browser and run the `<img>`. Any other tag (`portal`, a custom element) is
removed and its children are kept, so the tag cannot run and the text is not
thrown away. `style`, `meta`, and `link` are not fragment tags.

**Tree.** The string is parsed into the tree a browser builds (HTML spec
§13.2.6, #125): end tags are implied (`<p>one<p>two` is two paragraphs,
`<li>` closes an open `li`, `<td>` a cell, `<option>` an option, `<rt>` a
`rt`; a block start tag closes an open `p`), a table gets its implied
`tbody` / `tr` / `colgroup`, a stray `</p>` is `<p></p>` and `</br>` is
`<br>`, a breakout tag (`<p>`, `<div>`, `<img>`, …) ends `<svg>` / `<math>`,
and `<div/>` opens a `div`. As in Chromium, an element opened below 512
others is attached next to the 512th, so a parsed tree is at most 512 deep
(`parse_html.MAX_TREE_DEPTH`). Parsing, the sanitizer's walk and rendering
use their own stacks, not recursion: no input raises `RecursionError`, and
time is linear in the input. A tree built with the DOM API is not capped
and also renders at any depth. Not modelled, so the tree can still differ
from a browser's: the adoption agency for formatting elements
(`<b>1<p>2</b>3`), foster parenting of content placed directly in a
`<table>`, the form element pointer after its `form` is closed by another
end tag, and the context element (a `<tr>` outside a table is kept, since
the fragment may be inserted into one).

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
`src`, `action`, `formaction`, `srcset`, …) is dropped unless it passes the
renderer's URL allow-list (step 2 above), so a kept URL renders as written and
never becomes `about:invalid#ux-dom-unsafe-url` (#126). `style` drops
`expression(`, `javascript:`, and `vbscript:`.

**Text.** Text is escaped whether `escape` is true or false, so a `<` in a
text node cannot be parsed again as a tag. Numeric references are re-emitted
as written (`&#39;`, `&#x61;`). Named references are decoded with the HTML5
table, case-sensitive like a browser (`&AMP;` and `&amp;` are `&`), then
escaped. A name the table does not know is literal text, so `AT&T` stays
`AT&T`. Whitespace is kept as written, as a browser keeps it in the DOM:
a space or newline between inline tags (`<b>a</b>\n<i>b</i>`) and the body
of `pre`, `listing` and `textarea`. The one LF right after those three start
tags is dropped, as the browser drops it, and the renderer writes one more
before a body that starts with an LF, so a parse and a render round-trip
(#127). CRLF and a lone CR become LF, as the browser's input stream makes
them.

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
`tests/07_resilience/test_html_string_mxss.py`,
`tests/07_resilience/test_sanitized_stream.py`,
`tests/07_resilience/test_html_tree_construction.py`.
