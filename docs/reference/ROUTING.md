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

## No pure-dom router

ux-dom ships no file router. `ux_dom.routing`, the `DirectoryRouting` plugin,
`App.routes()` and `uxdom add route` were removed (F-18). Pure-dom demos wire
explicit FastAPI routes (`app.get("/x")(lambda: HTMLResponse(Page()))`).
Reserved method names on a `Component` (or any tag subclass; a mixin earlier
in the MRO counts too) raise `TypeError` at class creation:

- the sealed query API `get` / `matches` (customize queries by overriding
  `_find` / `_matches`);
- the old names of the renamed mutators `clear`, `remove`, `set_attribute`,
  `delete_attribute`, `setdocument`, `replace_children` (override the `_`
  name, e.g. `_set_attribute`, which is the supported hook).

Every other name, including `add` (e.g. a channel `@action def add`), is free:
library internals attach children via `_add`, so overriding `add` changes only
explicit `.add()` calls. Override `_add` to customize attachment from
constructor args, `with` blocks and `+=`.

## What ux-dom does **not** own

| Concern | Use |
|---------|-----|
| Product DirectoryRoutes | `ux_compose.routing` |
| create-app / build / serve | `uxcompose` |
| Host strategy / HMR | `uxcompose serve` |
| App CSS folders | `ux_compose.WebAssets` |

See [ux-compose FLOW](https://github.com/bitplorer/ux-compose/blob/main/docs/FLOW.md) for the ownership map.

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

    @action(caps=())
    def inc(self):
        self.n = int(self.n) + 1


def page_view():
    """GET handler: a module-level function, not a ``get`` classmethod."""
    from document import page
    return page(Hello().render())
```

HTMX is **opt-in** at the Document layer, not a hard dependency.
