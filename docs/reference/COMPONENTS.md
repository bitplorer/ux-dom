# Components & DOM

> **Diátaxis:** reference · **Canonical:** `docs/reference/COMPONENTS.md` · **Layer:** ux-dom  
> Map: [INDEX.md](../INDEX.md).

## Tags

```python
from ux_dom.dom import div, span, button, a

node = div(span("hi"), className="card", id="c1")
html = str(node)                 # pretty by default
compact = node.__render__(pretty=False)
```

Attribute dialects (HTMX / Alpine) are cleaned on emit (`hx_get` → `hx-get`, etc.).

## Component

```python
from dataclasses import dataclass
from ux_dom import Component
from ux_dom.dom import div, span

@dataclass(eq=False)
class Card(Component):
    title: str
    price: int = 0

    def render(self, title, price=0):
        return div(
            span(title),
            span(str(price), className="price"),
            className="card",
        )

html = str(Card(title="Tea", price=3))
```

- Implement **`render`** → return a tag tree (or markdown string / file path).
- `@dataclass` fields are supported (lazy init chain).
- `render_tag` stays `False` for Components (transparent root).

## Conditional children

```python
div(
    show and span("visible"),  # False → skipped
    None,                      # skipped
    0,                         # kept ("0")
    "ok",
)
```

## Context managers

```python
with div(id="root") as root:
    span("a")
    span("b")
# build only — then serialize root

async with div(id="root") as root:
    span("a")
html = "".join([x async for x in root.__async_render__(pretty=False)])
```

Sync and async stacks use ContextVars (task-isolated). See [CONTEXT_SYNC_ASYNC.md](../internals/CONTEXT_SYNC_ASYNC.md).

## Membership API

| API | Scope |
|-----|--------|
| **`node.matches(query)`** | This node only (+ Component `_entry` face) |
| **`node.get(query)`** | Self + entire subtree (list) |
| **`item in node`** | Existence under self/subtree (lazy) |
| **`bool(node)`** | Always `True` (instance exists) |
| **`len(node)`** | Child count |

```python
card = Card(title="x")
assert card.matches(Card)
assert span in card          # descendant class
assert card in card          # own existence (intentional)
```

Details: [MEMBERSHIP.md](../internals/MEMBERSHIP.md).

## ReactiveComponent

See [REACTIVE.md](REACTIVE.md) for stateful re-render components.

## Fragment

`Fragment` merges children without an extra wrapper element.

## Render phases

Build (`with`) vs serialize (`str` / `__render__` / stream): [RENDER_PHASES.md](../internals/RENDER_PHASES.md).
