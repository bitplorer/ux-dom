# Routing — DirectoryRouter

Next.js-style **file-based routes** for FastAPI.

## Layout

```text
app/routes/
  index.py              →  /index/Index   (class Index)
  users/[id].py         →  /users/{id}/…  (Python can't use {id} as filename)
  blog/[slug]/py        →  /blog/{slug}/…
  api/health.py         →  /api/health/…
```

Bracket folders/files are intentional: `[id]` → FastAPI `{id}`.

## Component routes

```python
# app/routes/index.py
from ux_dom import Component
from ux_dom.dom import div, h1
from app.document import page

class Index(Component):
    routes = ["get"]

    def render(self):
        return div(h1("Home"))

    @classmethod
    def get(cls):
        return page(cls(), page_title="Home")
```

`routes = ["get"]` exposes HTTP verbs as classmethods.

## Wire into FastAPI

```python
from ux_dom.plugins.routing import DirectoryRouting

DirectoryRouting(
    package_dir=PACKAGE,          # app package
    base_directory="routes",      # relative folder
    prefix="",                    # optional URL prefix
).include(app)
```

Scaffold `main.py` does this after `document.mount(app)`.

## Cleaning rules

- Package root stripped (`app/routes/users/[id]` → `/users/{id}`).
- Path traversal segments rejected/cleaned.
- See tests under `tests/test_directory_router*.py`.

## Partial HTMX endpoints

Return a Component or fragment **without** full `page()` for swaps:

```python
class Partial(Component):
    routes = ["get"]
    def render(self):
        return div("only this")
    @classmethod
    def get(cls):
        return cls()  # no document shell
```
