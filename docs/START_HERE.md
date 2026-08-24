# Start here — ux-dom 0.1.0 (mental model)

> **5-minute path (root):** [../START_HERE.md](../START_HERE.md)
> **Boundary:** [internals/SYSTEM.md](internals/SYSTEM.md)
> **Product apps:** [ux-compose](https://github.com/bitplorer/ux-compose) — `uxcompose create-app | serve | deploy`
> **Map:** [INDEX.md](INDEX.md)
> **Features:** [FEATURES.md](FEATURES.md)

### Brand lines

| Layer | Name |
|-------|------|
| **PyPI / pip** | `ux-dom` |
| **Import** | `ux_dom` |
| **CLI** | **`uxdom`** (pure-dom tooling) |
| **Product CLI** | **`uxcompose`** |

## Mental model

```text
ux-dom       RENDER     trees → __render__ / __async_render__
             Document   shell (.use: control, runtime, CSP stamp)
             discovery  pure DirectoryRoutes + RouterHooks

ux-compose   PRODUCT    create-app · serve · deploy · App · delivery
```

| Owns (ux-dom) | Does **not** own |
|---------------|------------------|
| Document shell, serialize, pure discovery | Product scaffold / serve / deploy |
| Pure-dom doctor / lint / build | Host strategy / product App |
| HTML/CSS/JS trees, package static | Intent / Cap / Result, MorphState, motion IR |

## Day-1 (product app)

```bash
pip install ux-compose ux-dom
uxcompose create-app myapp && cd myapp
uxcompose serve app:asgi --port 8080
```

## Pure Document

```python
from ux_dom import Document
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
uxdom profile
```

## Core concepts

| Piece | Role |
|-------|------|
| **`Component`** | `render()` → DOM tree |
| **`ReactiveComponent`** | Field mutation re-renders on serialize |
| **`document(*content)`** | HTML shell SSoT |
| **`DirectoryRoutes`** | Host-free path discovery |
| **`XElement`** | Custom element + definitions |

## Next reading

1. [../START_HERE.md](../START_HERE.md) — 5-minute path
2. [SYSTEM.md](internals/SYSTEM.md)
3. [DOCUMENT.md](guides/DOCUMENT.md)
4. [CLI.md](guides/CLI.md) · [DX.md](guides/DX.md)
5. ux-compose `docs/FLOW.md`
6. [INDEX.md](INDEX.md)

## Assets

* Library JS: `/ux-dom/static/x_element.js` from installed package
* App files: `/assets/*` → project `assets/`

## Quality

```bash
sh scripts/quality.sh
uxdom doctor
```
