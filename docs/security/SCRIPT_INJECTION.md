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
`</script` → `<\/script` and `<!--` → `<\!--` in scripts, `</style` →
`<\/style` in styles. These forms mean the same thing inside JS and CSS
strings, so user data embedded in an inline script cannot close the tag.
`raw(...)` children are still emitted untouched (explicit opt-out).

Embedding untrusted data in JS is still a JS-context problem: serialize it
with `json.dumps` (or a `data-*` attribute) rather than string concatenation.

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
