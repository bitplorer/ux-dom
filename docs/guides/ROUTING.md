# File-based routing (DirectoryRoutes)

## Design overview

File-based routing maps a **directory tree of Python modules** onto URL
paths — Python-native, filesystem-first. **Core is host-agnostic**; FastAPI is
one adapter.

**Preferred bind (composition roots including ux-compose):**
`DirectoryRoutes` + thin adapter. `DirectoryRouter` is batteries-only.


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

Preferred:

```python
from ux_dom.routing.core import DirectoryRoutes, RouterHooks
from ux_dom.routing.adapters.fastapi import mount

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

## Core + adapter (no host lock-in)

| Module | Role |
|--------|------|
| `ux_dom.routing.core` | Path law, page unit, `RouterHooks`, `DirectoryRoutes.discover()`, `RouteRecord` — **no FastAPI imports** |
| `ux_dom.routing.adapters.fastapi` | Thin **materialize/mount** from core records → APIRouter |
| `ux_dom.routing.fastapi.DirectoryRouter` | Full-featured FastAPI path (StreamingRoute, `[id]`, route modules) |

```python
from ux_dom.routing.core import DirectoryRoutes, RouterHooks
from ux_dom.routing.adapters.fastapi import mount

core = DirectoryRoutes(PACKAGE, hooks=hooks, fail_closed=True)
mount(core, api)  # include_router under the hood
```

`DirectoryRouter` remains the full-featured FastAPI path. Both share path law +
page unit + `RouterHooks`. Starlette adapter can land later without page-unit changes.

### Ownership (composition roots)

Composition roots (**ux-compose** and others) **must** use pure `DirectoryRoutes` + thin adapters
(`routing.adapters.fastapi.mount` / `adapters.asgi`).

`DirectoryRouter` is a **convenience batteries path for standalone FastAPI users of ux-dom only**.
It is **not** the primary integration contract for any author or composition layer.

See ux-compose `docs/FLOW.md` for the full residual-free ownership map.

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

See [ARCHITECTURE.md](../internals/ARCHITECTURE.md) · [CLI.md](CLI.md).

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
