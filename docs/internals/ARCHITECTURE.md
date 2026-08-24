# Architecture

## Design overview

ux-dom splits **HTML ownership** from **process ownership** so placement is never
guesswork and the ASGI host stays debuggable:

```text
┌─────────────────────────────────────────────────────────┐
│  Your app                                                │
│    routes/*.py   document.py   main.py                   │
│    (prefer: uxcompose create-app for product files)      │
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
| **`DirectoryRouter`** | Leftover FastAPI file router (demosite / examples) |
| **`CreateProject` / CLI** | `write()` fails closed — product scaffold is uxcompose |
| **`CreateAsgi`** | Fail-closed teaching stub |
| **`App` / `PluginHub`** | Optional registry; leftover batteries — not product |

## Canonical assembly

```python
from fastapi import FastAPI
from ux_dom.routing.fastapi import DirectoryRouter, StreamingRoute
from app.document import document

app = FastAPI(title="MyApp", debug=True)
document.mount(app)
app.include_router(
    DirectoryRouter(
        base_directory="routes",
        package_dir=PACKAGE,
        route_class=StreamingRoute,
    )
)
```

Greenfield: **`uxcompose create-app`**. Hand-roll this render bind only when
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
| DirectoryRoutes + adapters | `ux_dom/routing/core.py`, `routing/adapters/` |
| DirectoryRouter (batteries) | `ux_dom/routing/fastapi.py` |
| Package static | `ux_dom/plugins/safe_static.py`, `plugins/runtime.py` |
| Pure-dom generators | `ux_dom/cli/adders.py` (scaffold teaches uxcompose) |

Full path table: [MODULE_MAP.md](MODULE_MAP.md). Design intent: [DESIGN_CANON.md](DESIGN_CANON.md).

## Security surfaces

- [CSP.md](../security/CSP.md) — per-request nonce
- [SAFE_STATIC.md](../security/SAFE_STATIC.md) — package static allowlist

## What must not regress

[MAINTENANCE_CANON.md](../ship/MAINTENANCE_CANON.md)
