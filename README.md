# ux-dom 0.1.0

**Python HTML for hypermedia apps** — server-rendered DOM, file-based routing,
HTMX / Alpine / Web Components (`XElement` + `x_element.js`). Optional live
control plane is a separate package (not part of these brand lines).

> **Start here:** [docs/START_HERE.md](docs/START_HERE.md)  
> **Full docs index:** [docs/README.md](docs/README.md)  
> **Feature encyclopedia:** [docs/FEATURES.md](docs/FEATURES.md)

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

---

## Documentation

### Day-1

| Doc | Topic |
|-----|--------|
| [docs/START_HERE.md](docs/START_HERE.md) | One-page orientation |
| [docs/INSTALL.md](docs/INSTALL.md) | Install & extras |
| [docs/TUTORIAL.md](docs/TUTORIAL.md) | First app walkthrough |
| [docs/CLI.md](docs/CLI.md) | create-app, doctor, add |

### Core

| Doc | Topic |
|-----|--------|
| [docs/DOCUMENT.md](docs/DOCUMENT.md) | Document SSoT — head/body, `.use`, `.mount` |
| [docs/COMPONENTS.md](docs/COMPONENTS.md) | Component, Fragment, membership |
| [docs/REACTIVE.md](docs/REACTIVE.md) | ReactiveComponent (stateful re-render) |
| [docs/ROUTING.md](docs/ROUTING.md) | DirectoryRouter (`[id]` → `{id}`) |
| [docs/XELEMENT.md](docs/XELEMENT.md) | Custom elements + `x_element.js` |
| [docs/CSP.md](docs/CSP.md) | Nonce CSP (`Csp.auto`) |
| [docs/COOKBOOK.md](docs/COOKBOOK.md) | Short recipes |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Ownership diagram |

### Deep dives

| Doc | Topic |
|-----|--------|
| [docs/HYPERMEDIA.md](docs/HYPERMEDIA.md) | HTMX, Alpine, slots |
| [docs/SAFE_STATIC.md](docs/SAFE_STATIC.md) | Package static allowlist |
| [docs/ASSETS.md](docs/ASSETS.md) | WebAssets / Tailwind |
| [docs/RENDER_PHASES.md](docs/RENDER_PHASES.md) | Build vs serialize |
| [docs/CONTEXT_SYNC_ASYNC.md](docs/CONTEXT_SYNC_ASYNC.md) | Sync/async `with` |
| [docs/MEMBERSHIP.md](docs/MEMBERSHIP.md) | `get` / `in` / `matches` |
| [docs/PRETTY_STREAM.md](docs/PRETTY_STREAM.md) | Pretty streaming |
| [docs/CONCURRENCY.md](docs/CONCURRENCY.md) | Context stacks |
| [docs/UI.md](docs/UI.md) | Optional UI kit |
| [docs/DEPLOY.md](docs/DEPLOY.md) | Deploy |
| [docs/DX.md](docs/DX.md) | DX overview |
| [docs/COVERAGE.md](docs/COVERAGE.md) | Coverage policy |
| [docs/PUBLISHING.md](docs/PUBLISHING.md) | Release notes |
| [docs/PRODUCTION_READINESS.md](docs/PRODUCTION_READINESS.md) | Ship checklist |
| [docs/MAINTENANCE_CANON.md](docs/MAINTENANCE_CANON.md) | What must not regress |
| [CHANGELOG.md](CHANGELOG.md) | Version history |

Archive (audits): [docs/archive/](docs/archive/)

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
