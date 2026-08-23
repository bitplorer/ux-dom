# App composition

## Design overview

An ux-dom app is **three explicit pieces** — never a mega-hub that guesses
where tags go:

```text
Document  →  HTML shell (<head>/<body>), .use(runtimes), .mount(app)
FastAPI   →  process, routes, lifespan, servers
Routes    →  DirectoryRoutes (files) + thin adapter, or explicit FastAPI handlers
```

| Piece | Owns | Does not own |
|-------|------|--------------|
| **Document** | Tag placement, runtime scripts, CSP stamp, static allowlist | ASGI process |
| **FastAPI** | HTTP/WS lifecycle | Head/body order |
| **DirectoryRoutes** | File → path discovery | Document head |

## Canonical assembly

```python
from fastapi import FastAPI
from ux_dom import Document
from ux_dom.runtime import XElement, Htmx, Csp
from ux_dom.routing.core import DirectoryRoutes
from ux_dom.routing.adapters.fastapi import mount
from app import PACKAGE  # package root for file routes

document = Document(head=[], body=[], ensure_csrf_token=False).use(
    XElement(),
    Htmx(),
    Csp.auto(),
)

app = FastAPI(title="MyApp")
document.mount(app)
core = DirectoryRoutes(PACKAGE, base_directory="routes")
core.discover()
mount(core, app)
```

Greenfield product apps: **`uxcompose create-app`**. Hand-assemble this
render + host pattern only when extending composition contracts.

## Optional surfaces (not the document)

| API | Role |
|-----|------|
| `CreateAsgi` | One-liner sugar around FastAPI + document |
| `ux_dom.plugins.App` / PluginHub | Optional hub registration; **tests / advanced only** |
| `document(*page)` | Per-request two-stage head/body (see [DOCUMENT_TWO_STAGE.md](DOCUMENT_TWO_STAGE.md)) |

create-app does **not** use `App.web` as the document.

## Implementation map

| Concern | Module |
|---------|--------|
| Document factory + `.use` / `.mount` | `ux_dom/settings/document.py` |
| Runtime facades | `ux_dom/runtime/` |
| Directory routing helper | `ux_dom/plugins/routing/directory.py` |
| Scaffold | `ux_dom/cli/scaffold.py` |

**Further reading:** [DOCUMENT.md](DOCUMENT.md) · [ARCHITECTURE.md](../internals/ARCHITECTURE.md) ·
[DOCUMENT_AND_APP.md](DOCUMENT_AND_APP.md) · [START_HERE.md](../START_HERE.md).
