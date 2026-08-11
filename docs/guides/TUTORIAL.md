# Tutorial — first ux-dom app

## 1. Install & scaffold

```bash
pip install -e ".[fastapi]"
uxdom create-app hello
cd hello
```

## 2. Understand the three files

### `app/document.py`

- Builds **`document`** with shared head meta.
- **`.use(XElement(), Htmx(), Csp.auto())`** attaches runtimes.
- **`page()`** helper wraps content in the Document shell.

### `app/main.py`

```text
FastAPI → document.mount(app) → DirectoryRouting → optional /assets
```

No second framework — plain FastAPI.

### `app/routes/index.py`

A `Component` with `routes = ["get"]` and `get()` returning `page(...)`.

## 3. Run

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

- Visit `/index/Index`
- Visit `/health`

## 4. Add a page

```bash
# or hand-write app/routes/about.py
```

```python
from ux_dom import Component
from ux_dom.dom import div, h1, a
from app.document import page

class About(Component):
    routes = ["get"]
    def render(self):
        return div(
            a("Home", href="/index/Index"),
            h1("About"),
        )
    @classmethod
    def get(cls):
        return page(cls(), page_title="About")
```

URL: `/about/About` (DirectoryRouter naming).

## 5. Add HTMX

See scaffold tutorial routes or [COOKBOOK.md](COOKBOOK.md).

## 6. Custom element

```bash
uxdom add xelement Badge
# place host in a page — definitions auto-collected
```

## 7. Production posture

```bash
DEBUG=0 uvicorn app.main:app --host 0.0.0.0 --port 8080
# Csp.auto() switches to prod policy
uxdom doctor
```

Next: [DOCUMENT.md](DOCUMENT.md), [CSP.md](../security/CSP.md), [XELEMENT.md](XELEMENT.md).
