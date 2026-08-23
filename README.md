# ux-dom 0.1.0

**Python HTML for hypermedia apps** — server-rendered DOM, pure page discovery,
HTMX / Alpine / Web Components (`XElement` + `x_element.js`).

> **New here?** [START_HERE.md](START_HERE.md) (5 minutes).
> **Boundary:** [docs/internals/SYSTEM.md](docs/internals/SYSTEM.md)
> **Docs map:** [docs/INDEX.md](docs/INDEX.md)
> **Product apps:** [ux-compose](https://github.com/bitplorer/ux-compose) (`uxcompose create-app | serve | deploy`)

This layer **renders**. It does not own Intent, Caps, Result ops, product state
machines, motion IR, or author-facing composition.

```bash
pip install ux-dom
# Product app (composition + delivery) — not this package:
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

### Ownership

| Owns | Does **not** own |
|------|------------------|
| HTML/CSS/JS trees, `Document` shell, serialize | Intent / Cap / Result ops (`ux-channel`) |
| Pure `DirectoryRoutes` + `RouterHooks` | Product state machines (`ux-behavior`) |
| Package static (`/ux-dom/static/…`) | Motion IR (`ux-motion`) |
| Pure-dom CLI: `doctor` · `lint` · `build` · `profile` · `add` | Product scaffold / serve / deploy (`ux-compose`) |

---

## Audience

| You are… | Start |
|----------|--------|
| **New** | [START_HERE.md](START_HERE.md) |
| **Pure Document author** | [docs/guides/DOCUMENT.md](docs/guides/DOCUMENT.md) |
| **Product builder** | [ux-compose FLOW](https://github.com/bitplorer/ux-compose/blob/main/docs/FLOW.md) |
| **Contributor / agent** | [CONTRIBUTING.md](CONTRIBUTING.md) · [AGENTS.md](AGENTS.md) |
| **Need a map** | [docs/INDEX.md](docs/INDEX.md) |

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
| [START_HERE.md](START_HERE.md) | 5-minute path |
| [docs/INDEX.md](docs/INDEX.md) | Audience + Diátaxis map |
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
