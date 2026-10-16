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

## Pure-dom `DirectoryRouter` (examples, `uxdom add route`)

`ux_dom.routing.fastapi.DirectoryRouter` (or the `DirectoryRouting` plugin)
serves the examples and `uxdom add route` stubs. It uses the same path law,
and it fails closed wherever a mistake would otherwise be a silent 404:

| Rule | Detail |
|------|--------|
| **Stem match** | Case- and underscore-insensitive: `my_page.py` → `MyPage`, `wc.py` → `WC` |
| **No page unit** | A module that exports renderable classes but none matches the stem raises `DirectoryRouterError` (logged instead when `fail_closed=False`) |
| **Explicit `get`** | A `get` classmethod is served as-is (for example to wrap the page in a Document); the synthetic page GET is used only when there is none |
| **Sub-actions** | Non-verb names in `routes=` become `GET /<stem>/<name>`: `routes = ["get", "partial"]` → `/htmx/partial`. A listed name with no method on the class raises |
| **URLs in `routes=`** | Rejected: the URL comes from the file path, so `routes = ["/x/[id]"]` raises |
| **`route.py` / `index.py`** | Map to the folder prefix; `route.py` uses module-level verb functions (`def get(id: str)`) |

```text
routes/
  index.py                 →  GET /           (class Index)
  htmx.py                  →  GET /htmx, GET /htmx/partial  (class Htmx, routes=["get", "partial"])
  my_page.py               →  GET /my_page    (class MyPage)
  orgs/[org]/teams/[team]/route.py  →  GET /orgs/{org}/teams/{team}/  (def get(org, team))
```

`uxdom add route NAME [--methods get,post]` writes files that follow these rules.

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

    @classmethod
    def get(cls):
        from document import page
        return page(cls().render())

    @action(caps=())
    def inc(self):
        self.n = int(self.n) + 1
```

HTMX is **opt-in** at the Document layer, not a hard dependency.
