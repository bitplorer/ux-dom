# Script injection & double-injection policy

## Single source of truth for tags

```text
App.use(Contribution plugins)
        ↓
hub.shell_fragments(dedupe=True)
        ↓
document page() head/body
```

Do **not** also hardcode the same `<script src>` or call `ch.scripts()` on every
page if the hub already contributes those URLs.

## How double injection is prevented

### 1. Plugin identity (by name)

```python
hub.add_contribution(XElementRuntime())
hub.add_contribution(XElementRuntime())  # same name → replaces, not stacks
```

One entry per `plugin.name` on the hub.

### 2. URL dedupe (by src / href)

`hub.shell_fragments()` and `shell_fragments()` run **`dedupe_dom_nodes`**:

- Key is **(tag, rel, url)** of the `script[src]` / `link[href]` node itself;
  the first node per key wins (`rel` compares as a token set, case-insensitive)  
- Later duplicates (same contribution emitting twice, or `extra_head` re-adding
  the runtime) are dropped  
- Different tag or `rel` is a different resource: `link rel="preconnect"` does not
  drop `link rel="stylesheet"`, and `link rel="preload"` does not drop the `script`  
- Wrappers (e.g. `div(script(src=…))`) and other nodes pass through untouched  
- Inline scripts (no src) are **not** collapsed  

### 3. Ownership rules (by design)

| Runtime | Tags | Bytes |
|---------|------|-------|
| XElement | `XElementRuntime` → shell_fragments | SafeStaticFile |
| uxchannel | `UxChannelRuntime` **or** `ch.scripts()` — **pick one** | channel mount |

Scaffold: document uses `shell_fragments` only; live routes do **not** also
`raw(ch.scripts())`.

## Inline `<script>` / `<style>` text (raw text elements)

`script` and `style` are HTML raw text elements: the browser never decodes
entities inside them, so ux-dom emits their **string** children verbatim:

```python
script("if (a < b && c) go();")   # <script>if (a < b && c) go();</script>
style("p > a { content: '&'; }")  # <style>p > a { content: '&'; }</style>
```

Only sequences that could end the element early are rewritten (any case):
`</script` → `<\/script` and `<!--` → `\u003C!--` in scripts, `</style` →
`<\/style` in styles. These forms mean the same thing inside JS strings, JSON
(`type="application/json"`, `importmap`), u-flag regexes and CSS strings, so
user data embedded in an inline script cannot close the tag.

The rewrite runs at **render time over the joined body** (sync and async,
pretty and compact), so a hazard split across children (`"</scr"`, `"ipt>"`),
appended later with `.add()`, or set by index is still caught. `raw(...)`
children skip HTML escaping but are part of that joined body.

### Inside `<svg>` / `<math>` (foreign content)

There `style` and `script` are SVG / MathML elements, not raw text: the HTML
parser reads their body as markup (HTML spec §13.2.6.5). So the body, after
the rewrite above, is emitted as one CDATA section, which the parser keeps
verbatim. A `]]>` in the body is split across two sections:

```python
svg(style("svg > rect { fill: red }"))
# <svg><style><![CDATA[svg > rect { fill: red }]]></style></svg>
```

An author's own outer `<![CDATA[ … ]]>` (the usual SVG idiom) is unwrapped
first, and the commented forms (`/*<![CDATA[*/ … /*]]>*/`,
`//<![CDATA[ … //]]>`) stay comments, so CDATA-wrapped SVG CSS and JS keep
working.

The renderer replays the parser's stack of open elements over the tags
written before the element. Raw text resumes below an HTML integration point
(SVG `foreignObject`, `desc`, `title`; MathML `annotation-xml` whose
`encoding` is `text/html` or `application/xhtml+xml`) and a MathML text
integration point (`mi`, `mo`, `mn`, `ms`, `mtext`). A breakout tag in foreign
content (`b`, `big`, `blockquote`, `body`, `br`, `center`, `code`, `dd`,
`div`, `dl`, `dt`, `em`, `embed`, `h1`–`h6`, `head`, `hr`, `i`, `img`, `li`,
`listing`, `menu`, `meta`, `nobr`, `ol`, `p`, `pre`, `ruby`, `s`, `small`,
`span`, `strong`, `strike`, `sub`, `sup`, `table`, `tt`, `u`, `ul`, `var`,
and `font` with `color`, `face` or `size`) pops back to HTML, for its
descendants and for every later sibling, until an `svg` / `math` opens
foreign content again:

```python
svg(div(), style("a > b { }"))
# <svg><div></div><style>a > b { }</style></svg>
```

Tag-less wrappers (`Component`, `PlaceholderTag`) do not change the context;
the tags a `lazy` sibling renders are not seen. Where the HTML rules may have
closed an element early (`<div>` closes a `<p>`, `<img>` is void, `<a>`
closes an `<a>`), the tree does not say which, so the body stays CDATA unless
it is raw text in every case: `math(mi(p(div(), mglyph(style(...)))))` is
CDATA. That never runs script; at worst the browser is in HTML and the CSS or
JS gets a literal `<![CDATA[`. An element no HTML rule closes early (`span`,
`div`, an unknown name such as `desc` or `mi`) stays open until its own end
tag, so `svg(desc(desc(), script(...)))` is raw text. Nest HTML under
`foreignObject`.

**A `raw()` / `Markup` string that opens `<svg>` or `<math>` is author trust
(ADR 0002).** The tree does not model a context opened by a string, so
`div(raw("<svg>"), style(data), raw("</svg>"))`, or a tag whose `open_tag` is
`Markup("<svg>")`, renders `style` as HTML raw text, and the browser parses its
body as SVG markup. If a `style` / `script` inside may carry data, build
`svg` / `math` as tags, not as `raw()` / `Markup`.

### Inside `textarea`, `title`, `xmp`, `iframe`, `noembed`, `noframes`, `noscript`

The parser reads the body of these elements as text up to their own end tag:
RCDATA for `textarea` / `title` (character references decoded), RAWTEXT for
the rest (`noscript` when scripting is on). A `style` / `script` body, a
comment or `raw()` anywhere below them is not escaped, so each element checks
its own joined body for `</name` (any ASCII case):

```python
textarea(style("</textarea><img src=x onerror=alert(1)>"))
# <textarea><style>&lt;/textarea><img src=x onerror=alert(1)></style></textarea>
noscript(style("</noscript><img src=x onerror=alert(1)>"))
# InvalidNodeContext: <noscript> is RAWTEXT: its content would end it early
```

In RCDATA `&lt;` reads as `<`, so the value is unchanged. RAWTEXT has no other
spelling, so the render raises `InvalidNodeContext`; `noscript(style(...),
img(...))` without that sequence renders as before. The check holds in every
namespace, because a breakout tag (`svg(p(textarea(...)))`) puts the parser
back in HTML. `plaintext` has no end tag, so nothing below it can end it.

Embedding untrusted data in JS is still a JS-context problem: serialize it
with `json.dumps` (or a `data-*` attribute) rather than string concatenation.

CSS rule nodes (`CSSClass`, `CSSId`, `CSS`, `Keyframes`, `CSSProperty` rules)
write their selector and rule text raw, values included
(`font_family="'Courier New'"` stays `'Courier New'`, #127), so they render
only inside `style` (directly, nested in another rule, or through
`rule & rule`) or standalone as CSS text. As the child of any other element, including through `lazy` (a
lazy result renders as a child at the lazy's position), they raise
`InvalidNodeContext` (a `ValueError`) instead of writing CSS into HTML context:

```python
style(btn(color="red"))  # <style>.btn{color:red;}</style>
div(btn(color="red"))    # InvalidNodeContext: btn is a CSS rule; render it inside <style>, not <div>
```

A value (a `Keyframes` step's too) stays one CSS value
([#136](https://github.com/bitplorer/ux-dom/issues/136)). A value that could
end its declaration or rule raises `InvalidCSSValue` (a `ValueError`): `;`,
`{` or `}` outside a string, an unclosed string or one with a newline,
unbalanced `()` / `[]`, a comment, a newline, or a backslash outside a string
(`\75rl(` spells `url(`). Escapes inside strings (`content: "\201C"`) are
fine. CSS allows a `{}` block in a custom property value (`--x: {color: red}`),
but it raises too: a block can carry declarations. A property name must be a
CSS ident (`color`, `-webkit-x`, `--x`; no escapes), or it raises. Each URL
a CSS function loads (`url()`, `image-set()`, `src()`, `image()`) gets the
attribute URL allowlist in any property, custom properties included; a value with a refused URL renders as
`about:invalid#ux-dom-unsafe-url`, so the browser drops that declaration
([ATTRIBUTES.md](ATTRIBUTES.md), step 6):

```python
style(btn(color="red} body{background:yellow"))  # InvalidCSSValue
style(btn(cursor="url(//cdn.example/x.png), auto"))
# <style>.btn{cursor:about:invalid#ux-dom-unsafe-url;}</style>
style(btn(font_family="'Courier New', mono", content='"a;b"'))  # unchanged
```

## What dedupe does *not* fix

- Two **different** URLs for the same library (e.g. CDN htmx + local htmx)  
- Manually building HTML strings outside `shell_fragments`  
- Browser extensions injecting scripts  

## Disable (rare)

```python
hub.shell_fragments(dedupe=False)
shell_fragments(hub, dedupe=False)
```

## Debug

```python
from ux_dom.plugins.dedupe import extract_script_srcs
head, body = shell_fragments(get_hub())
print(extract_script_srcs(*head, *body))
```
