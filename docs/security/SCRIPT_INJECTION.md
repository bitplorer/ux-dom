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

- First `script[src]` / `link[href]` for a given URL wins  
- Later duplicates (same contribution emitting twice, or `extra_head` re-adding
  the runtime) are dropped  
- Inline scripts (no src) are **not** collapsed  

### 3. Ownership rules (by design)

| Runtime | Tags | Bytes |
|---------|------|-------|
| XElement | `XElementRuntime` → shell_fragments | SafeStaticFile |
| HTMX CDN | `HtmxControl` body | CDN |
| uxchannel | `UxChannelRuntime` **or** `ch.scripts()` — **pick one** | channel mount |

Scaffold: document uses `shell_fragments` only; live routes do **not** also
`raw(ch.scripts())`.

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
