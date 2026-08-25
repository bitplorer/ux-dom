# File-based routing

> **Diátaxis:** reference · **Canonical:** `docs/reference/ROUTING.md` · **Layer:** ux-dom  
> Map: [INDEX.md](../INDEX.md).

**Product page routing lives on ux-compose:**
`from ux_compose.routing import DirectoryRoutes`.

This package owns **render**. Page-unit discovery for product apps is not
taught here as a primary path. Use compose.

## Product path (only)

```text
routes/
  hello.py                 →  GET /hello     (page unit: class Hello)
  shop/cart.py             →  GET /shop/cart (page unit: class Cart)
  users/[id]/profile.py   →  GET /users/{id}/profile
  index.py                 →  GET /
```

| Rule | Detail |
|------|--------|
| **URL** | Filesystem only (folder + file stem). Class name never in the path. |
| **Page unit** | Renderable class whose name matches the module stem (`cart.py` → `Cart`) |
| **Params** | `[id]` → `{id}` |
| **Private** | `_*.py` and `_` path segments skipped |
| **Ambiguity** | Fail closed |

### Mount (ux-compose)

```python
from pathlib import Path
from ux_compose.routing import DirectoryRoutes, RouterHooks
from ux_compose.routing.adapters.fastapi import mount

hooks = RouterHooks(
    resolve_unit=lambda cls, path, name: registry.get(
        str(getattr(cls, "id", None) or cls.__name__.lower())
    ),
)
core = DirectoryRoutes(
    Path(__file__).resolve().parent,
    base_directory="routes",
    hooks=hooks,
    fail_closed=True,
)
core.discover()
mount(core, app)
```

Or the product composition root:

```python
from pathlib import Path
from ux_compose.build import build
from document import document

app, asgi, bundle = build(
    Path(__file__).parent,
    host="auto",
    live="auto",
    level=1,
    document=document,
)
```

Scaffold: `uxcompose create-app`.

## What ux-dom does **not** own

| Concern | Use |
|---------|-----|
| Product DirectoryRoutes | `ux_compose.routing` |
| create-app / build / serve | `uxcompose` |
| Host strategy / HMR | `uxcompose serve` |
| App CSS folders | `ux_compose.WebAssets` |

Historical FastAPI batteries and host plugins on this package are fail-closed
or non-product. Do not cite them in new apps.

See ux-compose `docs/FLOW.md` for the ownership map.

## Page unit example

```python
from ux_compose import Component, MorphState, action, control, div, span, button

class Hello(Component):
    id = "hello"
    n = MorphState(0)

    def render(self):
        return div(
            span(str(self.n), className="text-2xl font-semibold"),
            button("+1", type="button", className="rounded-full px-4 py-2", **control("hello.inc")),
            id=self.id,
            className="flex items-center gap-3",
        )

    @classmethod
    def get(cls):
        from document import page
        return page(cls().render())

    @action(caps=())
    def inc(self):
        self.n = int(self.n) + 1
```

HTMX is **opt-in** at the Document layer, not a hard dependency.
