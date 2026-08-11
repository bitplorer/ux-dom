# Architecture

## Ownership (no guesswork)

```text
┌─────────────────────────────────────────────────────────┐
│  Your app                                                │
│    routes/*.py   document.py   main.py                   │
├─────────────────────────────────────────────────────────┤
│  Document (SSoT for HTML)                                │
│    head/body · .use(runtimes) · .mount(app) · page()     │
├─────────────────────────────────────────────────────────┤
│  Runtimes                                                │
│    XElement  Htmx  Csp  Channel.optional()               │
├─────────────────────────────────────────────────────────┤
│  Core DOM                                                │
│    Component · tags · render · with / async with         │
├─────────────────────────────────────────────────────────┤
│  FastAPI (process)                                       │
│    routes · middleware · static · lifespan               │
└─────────────────────────────────────────────────────────┘
```

| Piece | Responsibility |
|-------|----------------|
| **`Document`** | Where tags go; runtime attach; `mount` static/middleware |
| **`FastAPI`** | HTTP/WS process |
| **`DirectoryRouting`** | File-based routes onto FastAPI |
| **`CreateProject` / CLI** | Filesystem scaffold only |
| **`CreateAsgi`** | Optional one-liner sugar (not used by create-app) |
| **`App` / `PluginHub`** | Legacy registry; tests/optional |

## Canonical assembly

```python
from fastapi import FastAPI
from ux_dom.plugins.routing import DirectoryRouting
from app.document import document

app = FastAPI(title="MyApp", debug=True)
document.mount(app)
DirectoryRouting(package_dir=PACKAGE, base_directory="routes").include(app)
```

## Runtime placement defaults

| Runtime | Head | Body | On `mount` |
|---------|------|------|------------|
| **XElement** | `x_element.js` script | — | `/ux-dom/static/…` |
| **Htmx** | — | CDN/local scripts | HTMX middleware (optional) |
| **Csp** | — | — | CSP middleware + nonce |
| **Channel** | boot scripts | — | (channel package attach) |

## Two-stage Document

See [DOCUMENT.md](../guides/DOCUMENT.md) and [DOCUMENT_TWO_STAGE.md](../guides/DOCUMENT_TWO_STAGE.md).

```text
<head>  [call-time head]  then  [common_head / runtimes]
<body>  content  [call-time body]  placeholders  [common_body / HTMX]
```

## Security surfaces

- [CSP.md](../security/CSP.md) — per-request nonce
- [SAFE_STATIC.md](../security/SAFE_STATIC.md) — package static allowlist

## What must not regress

[MAINTENANCE_CANON.md](../ship/MAINTENANCE_CANON.md)
