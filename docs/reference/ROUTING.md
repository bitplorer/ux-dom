# File-based routing

> **Diátaxis:** reference · **Canonical:** `docs/reference/ROUTING.md` · **Layer:** ux-dom  
> Map: [INDEX.md](../INDEX.md).

**Product page routing is `ux_compose.routing.DirectoryRoutes`.** This page
documents leftover `DirectoryRouter` batteries for standalone FastAPI trees
that cannot import compose (demosite / leftover examples).

## Design overview

File-based routing maps a **directory tree of Python modules** onto URL
paths — Python-native, filesystem-first.

**Product bind:** `from ux_compose.routing import DirectoryRoutes` + thin adapter.
**Leftover bind:** `DirectoryRouter` (this package).


```text
app/routes/
  hello.py                 →  GET /hello     (page unit: class Hello)
  shop/cart.py             →  GET /shop/cart (page unit: class Cart)
  users/[id]/profile.py   →  GET /users/{id}/profile
  index.py                 →  GET /          (folder prefix)
```

| Layer | Role |
|-------|------|
| **On disk** | Package layout under `base_directory` (default `routes`) |
| **Discovery** | `DirectoryRoutes` / `DirectoryRouter` walks modules; prefers `__all__` |
| **Page unit** | Renderable class whose **name matches the module stem** (`cart.py` → `Cart`) |
| **HTTP** | Synthetic page GET via `resolve_unit` / `cls()`, or explicit `get`/`post`/… on the class |
| **URL cleaning** | Strip package root; map `[id]` → `{id}`; drop private `_` segments |

### Path law (fixed)

* URL = **filesystem only** (folder + file stem). **Class name never appears in the path.**
* `route.py` / `index.py` → folder prefix (or `/`).

### Page unit (default product path)

* Exports from `__all__` when present (Python-native allow-list).
* Page type = class whose name matches the module stem.
* Ambiguous page picks **fail closed** (`DirectoryRouterError`).
* GET: explicit `get` on the class if present, else synthetic page GET.
* Other HTTP verbs only when explicit methods exist (advanced opt-in).

### Generic hooks (host-agnostic)

Preferred (product — ux-compose):

```python
from ux_compose.routing import DirectoryRoutes, RouterHooks
from ux_compose.routing.adapters.fastapi import mount

hooks = RouterHooks(
    resolve_unit=lambda cls, path, name: registry.get(
        str(getattr(cls, "id", None) or cls.__name__.lower())
    ),
)
core = DirectoryRoutes(
    PACKAGE,
    base_directory="routes",
    hooks=hooks,
    fail_closed=True,
)
core.discover()
mount(core, app)
```

Batteries (standalone FastAPI users of ux-dom only):

```python
from ux_dom.routing.fastapi import DirectoryRouter, RouterHooks, StreamingRoute

hooks = RouterHooks(
    resolve_unit=lambda cls, path, name: registry.get(
        str(getattr(cls, "id", None) or cls.__name__.lower())
    ),
)
router = DirectoryRouter(
    base_directory="routes",
    package_dir=PACKAGE,
    route_class=StreamingRoute,
    hooks=hooks,
    fail_closed=True,
)
app.include_router(router)
```

## Leftover core + adapter (fail-closed on ux-dom)

| Module | Role |
|--------|------|
| `ux_compose.routing.core` | **Product** path law, page unit, `DirectoryRoutes.discover()` |
| `ux_compose.routing.adapters.fastapi` | **Product** materialize/mount |
| `ux_dom.routing.fastapi.DirectoryRouter` | Leftover FastAPI batteries (demosite / examples) |
| `ux_dom.routing.core` / `adapters` | Fail-closed teaching stubs |

```python
from ux_compose.routing import DirectoryRoutes, RouterHooks
from ux_compose.routing.adapters.fastapi import mount

core = DirectoryRoutes(PACKAGE, hooks=hooks, fail_closed=True)
mount(core, api)
```

`DirectoryRouter` remains leftover FastAPI batteries for trees that cannot
import compose. Product composition roots **must** use `ux_compose.routing`.

See ux-compose `docs/FLOW.md` for the ownership map.

## Control plane (related)

| Plugin | Role |
|--------|------|
| `ChannelControl` | Day-1 default — semantic `data-ux-*` attrs |
| `HtmxControl` | **Opt-in** HTMX |
| `NullControl` | Tests / static |

```python
from ux_dom.plugins.control import ChannelControl, HtmxControl
document.use(ChannelControl())   # preferred
# document.use(HtmxControl())    # opt-in only
```

See [ARCHITECTURE.md](../internals/ARCHITECTURE.md) · [CLI.md](../guides/CLI.md).

## `[id]` path segments

| On disk | FastAPI path |
|---------|--------------|
| `routes/users/[id]/` | `/users/{id}/…` |
| `routes/users/[id]/profile.py` | `/users/{id}/profile` |

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
```

## Compose product path

```python
from pathlib import Path
from fastapi import FastAPI
from ux_compose import App

api = FastAPI()
app = App.boot("Shop", level="auto")
bundle = app.mount(Path(__file__).parent, asgi_app=api, base="routes")
```

Scaffold (`uxcompose create-app`) emits this layout. HTMX is **opt-in**, not a hard dependency.
