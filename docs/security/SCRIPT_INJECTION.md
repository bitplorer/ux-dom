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
| HTMX CDN | `HtmxControl` body | CDN |
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

The renderer follows the parser's namespace rules down the parent chain. Raw
text resumes below an HTML integration point (SVG `foreignObject`, `desc`,
`title`; MathML `annotation-xml` whose `encoding` is `text/html` or
`application/xhtml+xml`) and a MathML text integration point (`mi`, `mo`,
`mn`, `ms`, `mtext`). Tag-less wrappers (`Component`, `PlaceholderTag`) and
`lazy` do not change the context. A breakout tag such as
`svg(div(style(...)))` puts the browser back in HTML, where `<![CDATA[` is
plain text: the CSS breaks, but the rewrite still stops the body from closing
the element. Nest HTML under `foreignObject`.

**A `raw()` / `Markup` string that opens `<svg>` or `<math>` is author trust
(ADR 0002).** The tree does not model a context opened by a string, so
`div(raw("<svg>"), style(data), raw("</svg>"))`, or a tag whose `open_tag` is
`Markup("<svg>")`, renders `style` as HTML raw text, and the browser parses its
body as SVG markup. If a `style` / `script` inside may carry data, build
`svg` / `math` as tags, not as `raw()` / `Markup`.

Embedding untrusted data in JS is still a JS-context problem: serialize it
with `json.dumps` (or a `data-*` attribute) rather than string concatenation.

CSS rule nodes (`CSSClass`, `CSSId`, `CSS`, `Keyframes`, `CSSProperty` rules)
write their selector and rule text raw, so they render only inside `style`
(directly, nested in another rule, or through `rule & rule`) or standalone as
CSS text. As the child of any other element, including through `lazy` (a
lazy result renders as a child at the lazy's position), they raise
`InvalidNodeContext` (a `ValueError`) instead of writing CSS into HTML context:

```python
style(btn(color="red"))  # <style>.btn{color:red;}</style>
div(btn(color="red"))    # InvalidNodeContext: btn is a CSS rule; render it inside <style>, not <div>
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
