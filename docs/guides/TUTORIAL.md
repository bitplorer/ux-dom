# Tutorial — first render + product app

> **Diátaxis:** how-to · **Canonical:** `docs/guides/TUTORIAL.md` · **Layer:** ux-dom  
> Map: [INDEX.md](../INDEX.md).

Product lifecycle is **ux-compose**. This page is the render-layer walkthrough.

## 1. Product path (recommended)

```bash
pip install ux-compose ux-dom
uxcompose create-app hello --host auto --level auto
cd hello
uxcompose serve app:asgi --port 8080
```

Page units live in `routes/`. `render()` returns ux-dom tag trees.

## 2. Pure Document (no product host)

```python
from ux_dom import Document, Component
from ux_dom.runtime import XElement, Htmx, Csp
from ux_dom.dom import div, h1

document = Document(head=[], body=[]).use(
    XElement(), Htmx(), Csp.auto()
)
html = document(div(h1("Hi"))).__render__()
```

```bash
uxdom doctor
uxdom lint
```

## 3. DirectoryRoutes (when you bind FastAPI yourself)

Preferred discovery is **pure `DirectoryRoutes` + a thin adapter**, not
`DirectoryRouter` (batteries path for standalone FastAPI users of ux-dom).

```python
from fastapi import FastAPI
from ux_dom.routing.core import DirectoryRoutes
from ux_dom.routing.adapters.fastapi import mount

app = FastAPI()
document.mount(app)
core = DirectoryRoutes(PACKAGE, base_directory="routes")
core.discover()
mount(core, app)
```

## 4. Add a page unit

Product apps: add `routes/about.py` (stem matches class name).

Pure-dom stub only:

```bash
uxdom add route about
```

```python
from ux_dom import Component
from ux_dom.dom import div, h1, a
from app.document import page

class About(Component):
    routes = ["get"]
    def render(self):
        return div(
            a("Home", href="/"),
            h1("About"),
        )
    @classmethod
    def get(cls):
        return page(cls(), page_title="About")
```

## 5. Custom element

```bash
uxdom add xelement Badge
```

## 6. Production posture

```bash
uxcompose deploy --provider docker
uxdom build
```

See [CLI.md](CLI.md) · ux-compose `docs/FLOW.md`.
