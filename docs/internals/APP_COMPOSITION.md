# App composition

> **Diátaxis:** explanation · **Canonical:** `docs/internals/APP_COMPOSITION.md` · **Layer:** ux-dom  
> Map: [INDEX.md](../INDEX.md).

## Design overview

**ux-dom renders.** Product composition (routes, host, assets, serve) is **ux-compose**.

```text
Document  →  HTML shell (<head>/<body>), .use(runtimes)
ux-compose →  DirectoryRoutes, WebAssets, build(), serve, deploy
```

| Piece | Owns | Does not own |
|-------|------|--------------|
| **Document** | Tag placement, runtime scripts, CSP stamp, package static | ASGI process, product routes |
| **ux-compose** | Page routes, host strategy, Tailwind, HMR, tunnel | DOM serialize |

## Product assembly (only path)

```bash
uxcompose create-app myapp && cd myapp
uxcompose build
uxcompose serve app:asgi --port 8080
```

Composition root emitted by create-app:

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

Page routes: `from ux_compose.routing import DirectoryRoutes`.
App CSS folders: `ux_compose.WebAssets`.

## Document shell (this package)

```python
from ux_dom import Document
from ux_dom.runtime import XElement, Htmx, Csp
from ux_dom.dom import div, h1

document = Document(head=[], body=[]).use(
    XElement(),
    Htmx(),
    Csp.auto(),
)
html = document(div(h1("Hi"))).__render__()
```

Document.use stamps control, runtime, CSP — **not** HMR, host strategy, or product App.

## Forbidden residuals

| Concern | Home |
|---------|------|
| Product DirectoryRoutes | `ux_compose.routing` |
| create-app / build / serve / deploy | `uxcompose` |
| WebAssets / Tailwind CLI | `ux-compose` |
| Host / HMR / tunnel | `uxcompose serve` |

Historical FastAPI batteries and host plugins on this package are fail-closed
or non-product. Do not cite them in new apps.

**Further reading:** [DOCUMENT.md](../reference/DOCUMENT.md) · [SYSTEM.md](SYSTEM.md) ·
ux-compose `docs/FLOW.md` · [START_HERE.md](../START_HERE.md).
