# DirectoryRouter / file-based routing

## Design overview

File-based routing maps a **directory tree of Python modules** onto FastAPI
paths — Python-native, filesystem-first:

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
| **Discovery** | `DirectoryRouter` walks modules; prefers `__all__` |
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

```python
from ux_dom.routing.fastapi import DirectoryRouter, RouterHooks, StreamingRoute

hooks = RouterHooks(
    resolve_unit=lambda cls, path, name: registry.get(
        str(getattr(cls, "id", None) or cls.__name__.lower())
    ),
    # accept_symbol=..., on_route=...,
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

| Hook | Role |
|------|------|
| `resolve_unit(cls, path, name)` | Request-time instance for the **synthetic page GET** only. `None` → `cls()`. Explicit `get`/`post`/… bypass it. |
| `accept_symbol(name, obj, module)` | Filter during discovery / page pick |
| `on_route(record)` | Called after a route is accepted |

Hosts typically key live instances by `cls.id` or `cls.__name__.lower()` (soft contract).

ux-compose `app.mount(...)` / `mount_surfaces(...)` wire `resolve_unit` automatically from `unit_registry`.

See [ARCHITECTURE.md](../internals/ARCHITECTURE.md) · [CLI.md](CLI.md).

## `[id]` path segments

Python cannot use `{id}` as a folder name. Folders named `[id]` **are a feature**:

| On disk | FastAPI path |
|---------|--------------|
| `routes/users/[id]/` | `/users/{id}/…` |
| `routes/users/[id]/profile.py` | `/users/{id}/profile` (stem `profile` → class `Profile`) |

Do **not** “fix” brackets by stripping them without converting to `{id}`.

## Page unit example

```python
# routes/hello.py
from ux_compose import Component, MorphState, action, control

class Hello(Component):
    id = "hello"
    n = MorphState(0)

    def render(self):
        attrs = control("inc")
        attr_str = " ".join(f'{k}="{v}"' for k, v in attrs.items())
        return f'<div id="hello"><span>{self.n}</span><button {attr_str}>+1</button></div>'

    @action(caps=())
    def inc(self):
        self.n = int(self.n) + 1
```

Stem match: `hello.py` → `Hello`. No class name in the URL (`/hello`).

## Explicit HTTP methods (advanced opt-in)

```python
class Cart:
    def render(self):
        return "<div>cart</div>"

    def get(self):
        return self.render()

    def post(self):
        ...
```

Explicit methods are registered as-is and **do not** go through `resolve_unit`.

## Cleaning rules

- Package root stripped (`app/routes/users/[id]` → `/users/{id}`).
- Path traversal segments rejected/cleaned.
- Underscore-prefixed files/folders skipped.
- See tests: `tests/03_routing_cli/test_directory_router.py`.

## Compose product path

```python
from pathlib import Path
from fastapi import FastAPI
from ux_compose import App

api = FastAPI()
app = App.boot("Shop", level=1)
bundle = app.mount(Path(__file__).parent, asgi_app=api, base="routes")
# bundle.route_table / bundle.unit_registry available for doctor / CI
```

Scaffold (`uxcompose create-app`) emits this layout by default.
