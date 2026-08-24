# ux-dom

[![Python 3.14](https://img.shields.io/badge/python-3.14-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

Python HTML for hypermedia apps — server-rendered DOM, Document shell, pure page discovery.

Optional runtimes: HTMX, Alpine, `XElement`.

This layer **renders**. It does not own Intent, Caps, Result ops, product state machines, motion IR, or author-facing composition.

| Layer | Name |
|-------|------|
| **PyPI / pip** | `ux-dom` |
| **Import** | `ux_dom` |
| **CLI** | **`uxdom`** (pure-dom tooling) |
| **Product CLI** | **`uxcompose`** ([ux-compose](https://github.com/bitplorer/ux-compose)) |
| **Version** | `0.1.0` |
| **Python** | ≥ 3.14 (full stack) |
| **License** | [MIT](LICENSE) |

## Table of Contents

- [Install](#install)
- [Usage](#usage)
- [Ownership](#ownership)
- [Audience](#audience)
- [Mental model](#mental-model)
- [Pure-dom CLI](#pure-dom-cli)
- [Documentation](#documentation)
- [API](#api)
- [Quality](#quality)
- [Security](#security)
- [Contributing](#contributing)
- [License](#license)

## Install

```bash
pip install ux-dom
# extras:
pip install "ux-dom[fastapi]"      # FastAPI + uvicorn + multipart
pip install "ux-dom[dev]"          # tailwind, watchfiles, uvicorn
pip install "ux-dom[fastapidev]"   # both
```

From this tree:

```bash
pip install -e .
python -c "from ux_dom import Document; print(Document)"
```

**Greenfield product apps** are not this package’s job:

```bash
uxcompose create-app myapp && cd myapp
uxcompose build
uxcompose serve app:asgi --port 8080
```

See [INSTALL.md](INSTALL.md) and [docs/INSTALL.md](docs/INSTALL.md).

## Usage

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

Serialize SSoT: `tree.__render__()` / `tree.__async_render__()`. Optional HTTP adapters under `ux_dom.response` are **not** the product path.

Five-minute path: [START_HERE.md](START_HERE.md).

## Ownership

| Owns | Does **not** own |
|------|------------------|
| HTML/CSS/JS trees, `Document` shell, serialize | Intent / Cap / Result ops (`ux-channel`) |
| Pure `DirectoryRoutes` + `RouterHooks` | Product state machines (`ux-behavior`) |
| Package static (`/ux-dom/static/…`) | Motion IR (`ux-motion`) |
| Pure-dom CLI: `doctor` · `lint` · `profile` · `add` | Product scaffold / build / serve / deploy / CSS minify (`ux-compose`) |
| WebAssets *paths* (`discover_css_io`) | Tailwind CLI finder / download (`ux_compose.tailwind`) |

## Audience

| You are… | Start |
|----------|--------|
| **New** | [START_HERE.md](START_HERE.md) |
| **Pure Document author** | [docs/reference/DOCUMENT.md](docs/reference/DOCUMENT.md) |
| **Product builder** | [ux-compose FLOW](https://github.com/bitplorer/ux-compose/blob/main/docs/FLOW.md) |
| **Contributor / agent** | [CONTRIBUTING.md](CONTRIBUTING.md) · [AGENTS.md](AGENTS.md) |
| **Need a map** | [docs/INDEX.md](docs/INDEX.md) |
| **Security reviewer** | [SECURITY.md](SECURITY.md) · [docs/security/CSP.md](docs/security/CSP.md) |
| **Questions** | [SUPPORT.md](SUPPORT.md) |

## Mental model

```text
ux-dom       RENDER     trees → __render__ / __async_render__
             Document   shell (.use: control, runtime, CSP stamp)
             discovery  pure DirectoryRoutes + RouterHooks

ux-compose   PRODUCT    create-app · build · serve · deploy · App · delivery
```

**Greenfield product apps:** `uxcompose create-app` — not `uxdom create-app`.

## Pure-dom CLI

```bash
uxdom doctor
uxdom lint
uxdom profile
uxdom add component Card
```

Product CSS minify: **`uxcompose build`** (`ux_compose.tailwind` finds the CLI).
`uxdom build` remains Document/static verify for leftover `app/main.py` trees.

See [docs/guides/CLI.md](docs/guides/CLI.md). Product `serve` / `deploy` / tunnel: **ux-compose**.

## Documentation

Family contract: [docs/DOCUMENTATION.md](docs/DOCUMENTATION.md). Map: [docs/INDEX.md](docs/INDEX.md).

Canonical pages live under `docs/reference/`, `docs/guides/`, `docs/internals/`, `docs/security/`. Older paths such as `docs/guides/DOCUMENT.md` are **Moved stubs** — do not cite them.

| Diátaxis | Canonical |
|----------|-----------|
| Tutorial | [START_HERE.md](START_HERE.md) · [docs/guides/TUTORIAL.md](docs/guides/TUTORIAL.md) |
| How-to | [docs/guides/SNIPPETS.md](docs/guides/SNIPPETS.md) · [docs/guides/CLI.md](docs/guides/CLI.md) · [docs/guides/COOKBOOK.md](docs/guides/COOKBOOK.md) · [docs/guides/DX.md](docs/guides/DX.md) |
| Reference | [docs/reference/DOCUMENT.md](docs/reference/DOCUMENT.md) · [docs/reference/COMPONENTS.md](docs/reference/COMPONENTS.md) · [docs/reference/FEATURES.md](docs/reference/FEATURES.md) · [docs/reference/API_SURFACE.md](docs/reference/API_SURFACE.md) |
| Explanation | [docs/internals/SYSTEM.md](docs/internals/SYSTEM.md) · [docs/internals/ARCHITECTURE.md](docs/internals/ARCHITECTURE.md) |

## API

Typical imports (see `ux_dom/__init__.py` and [docs/reference/API_SURFACE.md](docs/reference/API_SURFACE.md)):

| Export | Role |
|--------|------|
| `Document` | HTML head/body SSoT; `.use(...)` for control, runtime, CSP |
| `Component`, `Fragment`, `ReactiveComponent` | Build trees |
| `XElement`, `Htmx`, `Csp` | Optional runtimes / nonce CSP |
| `ux_dom.dom` (`div`, `h1`, …) | Tag constructors |
| `ux_dom.routing.core` | Pure `DirectoryRoutes` + `RouterHooks` |
| `ux_dom.ui` | Optional copy-in UI kit |
| CLI `uxdom` | `ux_dom.cli:app` |

## Quality

```bash
sh scripts/quality.sh
```

## Security

Nonce CSP, safe static, and script-injection policy live under [docs/security/](docs/security/CSP.md). This layer does not mint Caps. Reporting: [SECURITY.md](SECURITY.md).

## Contributing

PRs are welcome. Read [CONTRIBUTING.md](CONTRIBUTING.md) and [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md). Questions: [SUPPORT.md](SUPPORT.md). Governance: [GOVERNANCE.md](GOVERNANCE.md). History: [CHANGELOG.md](CHANGELOG.md).

## License

MIT — see [LICENSE](LICENSE).
