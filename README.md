# ux-dom 0.1.0

**Python HTML for hypermedia apps** — server-rendered DOM, pure page discovery,
HTMX / Alpine / Web Components (`XElement` + `x_element.js`).

> **Boundary:** [docs/internals/SYSTEM.md](docs/internals/SYSTEM.md)  
> **Product apps:** use **[ux-compose](https://github.com/bitplorer/ux-compose)** (`uxcompose create-app | serve | deploy`)  
> **Feature map:** [docs/FEATURES.md](docs/FEATURES.md)

```bash
pip install ux-dom
# Product app (composition + delivery):
uxcompose create-app myapp && cd myapp
uxcompose serve app:asgi --port 8080
```

### Brand lines

| Layer | Name |
|-------|------|
| **PyPI / pip** | `ux-dom` |
| **Import** | `ux_dom` |
| **CLI** | **`uxdom`** (pure-dom tooling) |
| **Product CLI** | **`uxcompose`** |

---

## Mental model

```text
ux-dom       RENDER     trees → __render__ / __async_render__
             Document   shell (.use: control, runtime, CSP stamp)
             discovery  pure DirectoryRoutes + RouterHooks

ux-compose   PRODUCT    create-app · serve · deploy · App · delivery
```

```python
from ux_dom import Document, Component
from ux_dom.runtime import XElement, Htmx, Csp
from ux_dom.dom import div, h1

document = Document(head=[], body=[]).use(
    XElement(),
    Htmx(),
    Csp.auto(),
)

# Product HTTP host / routes: ux-compose App.mount (not plugins.App.web)
html = document(div(h1("Hi"))).__render__()
```

**Greenfield product apps:** `uxcompose create-app` — not `uxdom create-app`.

---

## Pure-dom CLI

```bash
uxdom doctor
uxdom lint
uxdom build
uxdom profile
uxdom add component Card
```

See [docs/guides/CLI.md](docs/guides/CLI.md) · [docs/guides/DX.md](docs/guides/DX.md).

---

## Documentation

| Doc | Topic |
|-----|--------|
| [SYSTEM.md](docs/internals/SYSTEM.md) | Render boundary |
| [DOCUMENT.md](docs/guides/DOCUMENT.md) | Document SSoT |
| [COMPONENTS.md](docs/guides/COMPONENTS.md) | Component / Fragment |
| [ROUTING.md](docs/guides/ROUTING.md) | Directory discovery |
| [XELEMENT.md](docs/guides/XELEMENT.md) | Custom elements |
| [CSP.md](docs/security/CSP.md) | Nonce CSP |
| [FEATURES.md](docs/FEATURES.md) | Feature map |

Product delivery / scaffold: **ux-compose** `docs/FLOW.md`.

---

## Quality

```bash
sh scripts/quality.sh
```

## License

MIT
