# Architecture

## Design overview

ux-dom splits **HTML ownership** from **process ownership** so placement is never
guesswork and the ASGI host stays debuggable:

```text
┌─────────────────────────────────────────────────────────┐
│  Product app (ux-compose)                                │
│    routes/*.py   document.py   app.py                    │
│    uxcompose create-app | build | serve | deploy         │
├─────────────────────────────────────────────────────────┤
│  Document (SSoT for HTML) — ux-dom                       │
│    head/body · .use(runtimes) · page()                   │
├─────────────────────────────────────────────────────────┤
│  Runtimes                                                │
│    XElement  Htmx  Csp                                   │
├─────────────────────────────────────────────────────────┤
│  Core DOM                                                │
│    Component · tags · render · with / async with         │
└─────────────────────────────────────────────────────────┘
```

| Piece | Responsibility |
|-------|----------------|
| **`Document`** | Where tags go; runtime attach; CSP stamp |
| **`ux-compose`** | Page routes (`DirectoryRoutes`), WebAssets, Tailwind, host, HMR, serve |
| **Pure-dom CLI** | `uxdom doctor | lint | profile | add` |

## Product assembly (only path)

```bash
uxcompose create-app myapp && cd myapp
uxcompose build
uxcompose serve app:asgi --port 8080
```

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

## Runtime placement defaults

| Runtime | Head | Body | On product serve |
|---------|------|------|------------------|
| **XElement** | `x_element.js` script | — | `/ux-dom/static/…` |
| **Htmx** | — | CDN/local scripts | optional middleware |
| **Csp** | — | — | CSP middleware + nonce |

## Two-stage Document

See [DOCUMENT.md](../guides/DOCUMENT.md) and [DOCUMENT_TWO_STAGE.md](../guides/DOCUMENT_TWO_STAGE.md).

```text
<head>  [call-time head]  then  [common_head / runtimes]
<body>  content  [call-time body]  placeholders  [common_body / HTMX]
```

## Implementation map

| Concern | Module |
|---------|--------|
| Document `.use` / stages | `ux_dom/settings/document.py` |
| HtmlDocument pre-render | `ux_dom/dom/htmldocument.py` |
| Component / Reactive | `ux_dom/dom/src/component.py` |
| Serialize / attr dialects | `ux_dom/dom/src/ext.py` |
| XElement host/definition | `ux_dom/dom/htmlelement.py` |
| Package static | `ux_dom/plugins/safe_static.py`, `plugins/runtime.py` |
| Pure-dom generators | `ux_dom/cli/adders.py` |
| Product DirectoryRoutes | **ux-compose** `ux_compose.routing` |
| Product WebAssets / Tailwind | **ux-compose** |

Full path table: [MODULE_MAP.md](MODULE_MAP.md). Design intent: [DESIGN_CANON.md](DESIGN_CANON.md).

## Security surfaces

- [CSP.md](../security/CSP.md) — per-request nonce
- [SAFE_STATIC.md](../security/SAFE_STATIC.md) — package static allowlist

## What must not regress

[MAINTENANCE_CANON.md](../ship/MAINTENANCE_CANON.md)
