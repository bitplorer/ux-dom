# Architecture

## Design overview

ux-dom splits **HTML ownership** from **process ownership** so placement is never
guesswork and the ASGI host stays debuggable:

```text
┌─────────────────────────────────────────────────────────┐
│  Your app                                                │
│    routes/*.py   document.py   main.py                   │
│    (prefer: uxdom create-app / add for ceremonial files) │
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
| **`App` / `PluginHub`** | Optional registry; tests/advanced only |

## Canonical assembly

```python
from fastapi import FastAPI
from ux_dom.plugins.routing import DirectoryRouting
from app.document import document

app = FastAPI(title="MyApp", debug=True)
document.mount(app)
DirectoryRouting(package_dir=PACKAGE, base_directory="routes").include(app)
```

Greenfield: **`uxdom create-app`** emits this pattern. Hand-roll only when
extending composition itself ([DX.md](../guides/DX.md)).

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

## Implementation map

| Concern | Module |
|---------|--------|
| Document `.use` / `.mount` / stages | `ux_dom/settings/document.py` |
| HtmlDocument pre-render | `ux_dom/dom/htmldocument.py` |
| Component / Reactive | `ux_dom/dom/src/component.py` |
| Serialize / attr dialects | `ux_dom/dom/src/ext.py` |
| XElement host/definition | `ux_dom/dom/htmlelement.py` |
| DirectoryRouter | `ux_dom/routing/fastapi.py` |
| Package static | `ux_dom/plugins/safe_static.py`, `plugins/runtime.py` |
| Scaffold / generators | `ux_dom/cli/scaffold.py`, `cli/adders.py` |

Full path table: [MODULE_MAP.md](MODULE_MAP.md). Design intent: [DESIGN_CANON.md](DESIGN_CANON.md).

## Security surfaces

- [CSP.md](../security/CSP.md) — per-request nonce
- [SAFE_STATIC.md](../security/SAFE_STATIC.md) — package static allowlist

## What must not regress

[MAINTENANCE_CANON.md](../ship/MAINTENANCE_CANON.md)
