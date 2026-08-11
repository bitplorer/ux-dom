# ux-dom 0.1.0

**Python HTML for hypermedia apps** — server-rendered DOM, file-based routing,
HTMX / Alpine / Web Components (`XElement` + `x_element.js`). Optional live
control plane is a separate package (not part of these brand lines).

> **Start here:** [docs/START_HERE.md](docs/START_HERE.md)  
> **Full docs index:** [docs/README.md](docs/README.md)  
> **Feature encyclopedia:** [docs/FEATURES.md](docs/FEATURES.md)  
> **Architecture:** [docs/internals/ARCHITECTURE.md](docs/internals/ARCHITECTURE.md) ·
> [docs/internals/DESIGN_CANON.md](docs/internals/DESIGN_CANON.md)

```bash
poetry install --extras fastapi
# or: pip install -e ".[fastapi]"
uxdom create-app myapp && cd myapp
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

### Brand lines

> Companion stack: [Stack with ux-channel](docs/STACK.md)

| Layer | Name |
|-------|------|
| **PyPI / pip** | `ux-dom` |
| **Import** | `ux_dom` |
| **CLI** | **`uxdom`** |

| | |
|--|--|
| **Version** | **0.1.0** |
| **Python** | **3.14** only (`pyproject.toml`) |
| **Layout** | `src/ux_dom` (Poetry) |
| **ASGI** | FastAPI via optional extra `[fastapi]` / `[fastapidev]` |
| **License** | MIT |

---

## Mental model

```text
Document  →  HTML shell (<head>/<body>) + .use(runtimes) + .mount(app)
FastAPI   →  process, routes, servers
CLI       →  create-app / add  (ceremonial files — prefer automation)
```

```python
from fastapi import FastAPI
from ux_dom import Document, Component, ReactiveComponent
from ux_dom.runtime import XElement, Htmx, Csp
from ux_dom.dom import div, h1

document = Document(head=[], body=[], ensure_csrf_token=False).use(
    XElement(),  # serves x_element.js
    Htmx(),
    Csp.auto(),
)

app = FastAPI(title="Hello")
document.mount(app)

@app.get("/")
def home():
    return document(div(h1("Hi")), page_title="Home")
```

**Greenfield default:** `uxdom create-app` — do not hand-roll the skeleton unless
you are extending features or changing contracts. See [docs/guides/DX.md](docs/guides/DX.md).

---

## Documentation

### Day-1

| Doc | Topic |
|-----|--------|
| [docs/START_HERE.md](docs/START_HERE.md) | One-page orientation |
| [docs/INSTALL.md](docs/INSTALL.md) | Install & extras |
| [docs/guides/TUTORIAL.md](docs/guides/TUTORIAL.md) | First app walkthrough |
| [docs/guides/CLI.md](docs/guides/CLI.md) | create-app, doctor, add |

### Core

| Doc | Topic |
|-----|--------|
| [docs/guides/DOCUMENT.md](docs/guides/DOCUMENT.md) | Document SSoT — head/body, `.use`, `.mount` |
| [docs/guides/COMPONENTS.md](docs/guides/COMPONENTS.md) | Component, Fragment, membership |
| [docs/guides/REACTIVE.md](docs/guides/REACTIVE.md) | ReactiveComponent (stateful re-render) |
| [docs/guides/ROUTING.md](docs/guides/ROUTING.md) | DirectoryRouter (`[id]` → `{id}`) |
| [docs/guides/XELEMENT.md](docs/guides/XELEMENT.md) | Custom elements + `x_element.js` |
| [docs/security/CSP.md](docs/security/CSP.md) | Nonce CSP (`Csp.auto`) |
| [docs/guides/COOKBOOK.md](docs/guides/COOKBOOK.md) | Short recipes |
| [docs/internals/ARCHITECTURE.md](docs/internals/ARCHITECTURE.md) | Ownership diagram |

### Deep dives

| Doc | Topic |
|-----|--------|
| [docs/guides/HYPERMEDIA.md](docs/guides/HYPERMEDIA.md) | HTMX, Alpine, slots |
| [docs/security/SAFE_STATIC.md](docs/security/SAFE_STATIC.md) | Package static allowlist |
| [docs/security/ASSETS.md](docs/security/ASSETS.md) | WebAssets / Tailwind |
| [docs/internals/RENDER_PHASES.md](docs/internals/RENDER_PHASES.md) | Build vs serialize |
| [docs/internals/CONTEXT_SYNC_ASYNC.md](docs/internals/CONTEXT_SYNC_ASYNC.md) | Sync/async `with` |
| [docs/internals/MEMBERSHIP.md](docs/internals/MEMBERSHIP.md) | `get` / `in` / `matches` |
| [docs/internals/PRETTY_STREAM.md](docs/internals/PRETTY_STREAM.md) | Pretty streaming |
| [docs/internals/CONCURRENCY.md](docs/internals/CONCURRENCY.md) | Context stacks |
| [docs/guides/UI.md](docs/guides/UI.md) | Optional UI kit |
| [docs/ship/DEPLOY.md](docs/ship/DEPLOY.md) | Deploy |
| [docs/guides/DX.md](docs/guides/DX.md) | DX + automation-first |
| [docs/ship/COVERAGE.md](docs/ship/COVERAGE.md) | Coverage policy |
| [docs/ship/PUBLISHING.md](docs/ship/PUBLISHING.md) | Release notes |
| [docs/ship/PRODUCTION_READINESS.md](docs/ship/PRODUCTION_READINESS.md) | Ship checklist |
| [docs/ship/MAINTENANCE_CANON.md](docs/ship/MAINTENANCE_CANON.md) | What must not regress |
| [CHANGELOG.md](CHANGELOG.md) | Version history |

Archive (historical only): [docs/archive/](docs/archive/)

---

## Quality

```bash
sh scripts/quality.sh
# black · ruff · mypy ux_dom · pytest
# coverage: pytest --cov=ux_dom  (fail_under=70)
```

---

## License

MIT
