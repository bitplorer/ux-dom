# App composition

> **Diátaxis:** explanation · **Canonical:** `docs/internals/APP_COMPOSITION.md` · **Layer:** ux-dom  
> Map: [INDEX.md](../INDEX.md).

## Design overview

An ux-dom app is **three explicit pieces** — never a mega-hub that guesses
where tags go:

```text
Document  →  HTML shell (<head>/<body>), .use(runtimes), .mount(app)
FastAPI   →  process, routes, lifespan, servers
Routes    →  leftover DirectoryRouter, or product ux_compose.routing
```

| Piece | Owns | Does not own |
|-------|------|--------------|
| **Document** | Tag placement, runtime scripts, CSP stamp, static allowlist | ASGI process |
| **FastAPI** | HTTP/WS lifecycle | Head/body order |
| **DirectoryRouter** | Leftover file → path (demosite) | Document head |

## Canonical assembly

```python
from fastapi import FastAPI
from ux_dom import Document
from ux_dom.runtime import XElement, Htmx, Csp
from ux_dom.routing.fastapi import DirectoryRouter, StreamingRoute
from app import PACKAGE  # package root for file routes

document = Document(head=[], body=[], ensure_csrf_token=False).use(
    XElement(),
    Htmx(),
    Csp.auto(),
)

app = FastAPI(title="MyApp")
document.mount(app)
app.include_router(
    DirectoryRouter(
        base_directory="routes",
        package_dir=PACKAGE,
        route_class=StreamingRoute,
    )
)
```

Greenfield product apps: **`uxcompose create-app`**. Hand-assemble this
render + host pattern only when extending composition contracts.

## Optional surfaces (not the document)

| API | Role |
|-----|------|
| `CreateAsgi` | One-liner sugar around FastAPI + document |
| `ux_dom.plugins.App` / PluginHub | Optional hub registration; **tests / advanced only** |
| `document(*page)` | Per-request two-stage head/body (see [DOCUMENT_TWO_STAGE.md](../reference/DOCUMENT_TWO_STAGE.md)) |

Product create-app is **uxcompose**; it does **not** use `App.web` as the document.

## Implementation map

| Concern | Module |
|---------|--------|
| Document factory + `.use` / `.mount` | `ux_dom/settings/document.py` |
| Runtime facades | `ux_dom/runtime/` |
| DirectoryRoutes + adapters | `ux_dom/routing/core.py`, `routing/adapters/` |
| Pure-dom add generators | `ux_dom/cli/adders.py` |

**Further reading:** [DOCUMENT.md](../reference/DOCUMENT.md) · [ARCHITECTURE.md](ARCHITECTURE.md) ·
[DOCUMENT_AND_APP.md](DOCUMENT_AND_APP.md) · [START_HERE.md](../START_HERE.md).
