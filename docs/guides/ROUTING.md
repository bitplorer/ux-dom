# DirectoryRouter / file-based routing

## Design overview

File-based routing maps a **directory tree of Python modules** onto FastAPI
paths — same idea as Next.js app router, but Python-native:

```text
app/routes/
  index.py              →  /index/Index  (or class routes=)
  shop/list.py          →  /shop/list/…
  users/[id]/route.py  →  /users/{id}/…   ([id] is intentional)
```

| Layer | Role |
|-------|------|
| **On disk** | Package layout under `base_directory` (default `routes`) |
| **Discovery** | `DirectoryRouter` / `DirectoryRouting` walks modules |
| **HTTP** | FastAPI routes registered from Component `routes=` or bare `get()` |
| **URL cleaning** | Strip package root; map `[id]` → `{id}`; drop private `_` segments |

Canonical assembly (scaffold default):

```python
from ux_dom.plugins.routing import DirectoryRouting

DirectoryRouting(
    package_dir=PACKAGE,          # app package root
    base_directory="routes",
).include(app)
```

See [ARCHITECTURE.md](../internals/ARCHITECTURE.md) · [CLI.md](CLI.md).

## `[id]` path segments

Python cannot use `{id}` as a folder name. Folders named `[id]` **are a feature**:

| On disk | FastAPI path |
|---------|--------------|
| `routes/users/[id]/` | `/users/{id}/…` |
| `routes/users/[id]/route.py` | class name appears in URL path |

Do **not** “fix” brackets by stripping them without converting to `{id}`.

## Component routes

```python
from ux_dom import Component
from ux_dom.dom import div, h1

class Settings(Component):
    routes = ["get"]

    @classmethod
    def get(cls):
        return div(h1("Settings"))
```

Path params must be **named** on the handler (not a catch-all `**path_params`):

```python
class Page(Component):
    routes = ["get"]

    @classmethod
    def get(cls, id: str):
        return div(h1(f"User {id}"))
```

Scaffold `main.py` does this after `document.mount(app)`.

## Cleaning rules

- Package root stripped (`app/routes/users/[id]` → `/users/{id}`).
- Path traversal segments rejected/cleaned.
- See tests: `tests/03_routing_cli/test_directory_router.py`.

## Partial HTMX endpoints

Return a Component or fragment **without** full `page()` for swaps:

```python
class Partial(Component):
    routes = ["get"]

    @classmethod
    def get(cls):
        return div("fragment only")
```

## Implementation map

| Module | Owns |
|--------|------|
| `ux_dom/routing/fastapi.py` | DirectoryRouter, StreamingRoute, path cleaning |
| `ux_dom/plugins/routing/directory.py` | `DirectoryRouting` scaffold helper |
| `ux_dom/cli/adders.py` | `uxdom add route` generator |
| `ux_dom/cli/scaffold.py` | create-app wires DirectoryRouting |

**Automation:** prefer `uxdom add route …` for new route modules — hand-edit only
to extend handlers or change URL contracts.
