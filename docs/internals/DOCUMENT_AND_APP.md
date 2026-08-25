# Document ↔ App

> **Diátaxis:** explanation · **Canonical:** `docs/internals/DOCUMENT_AND_APP.md` · **Layer:** ux-dom  
> Map: [INDEX.md](../INDEX.md).

## Design overview

**Document is the HTML SSoT.** Product “app” means the composition root on
**ux-compose** (`build()`, DirectoryRoutes, serve) — not a second document factory.

```text
                    ┌──────────────┐
  request ─────────►│  ux-compose  │── DirectoryRoutes / host / serve
                    └──────┬───────┘
                           │ document= from create-app
                    ┌──────▼───────┐
                    │  Document    │── head/body · runtimes · package static
                    └──────┬───────┘
                           │ document(*page)
                    ┌──────▼───────┐
                    │ Component    │── serialize → HTML / stream
                    │  tree        │
                    └──────────────┘
```

## Preferred pattern

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

## What `App` means in code

| Name | Meaning |
|------|---------|
| Everyday “app” | Product composition root on ux-compose |
| `ux_compose.App` / `build()` | Product path |
| `ux_dom.plugins.App` | Optional plugin hub (tests / advanced) — **not** the HTML shell |

## Automation

```bash
uxcompose create-app myapp
uxcompose doctor .
uxdom doctor          # pure Document health
```

Do not hand-reintroduce a parallel “App owns head/body” path on ux-dom.

**Canonical deep dives:** [DOCUMENT.md](../reference/DOCUMENT.md) · [APP_COMPOSITION.md](APP_COMPOSITION.md) ·
[SYSTEM.md](SYSTEM.md) · ux-compose `docs/FLOW.md`.
