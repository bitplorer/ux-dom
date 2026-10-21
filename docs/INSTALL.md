# Install

### Brand lines

| Layer | Name |
|-------|------|
| **PyPI / pip** | `ux-dom` |
| **Import** | `ux_dom` |
| **CLI** | **`uxdom`** (pure-dom tooling) |
| **Product CLI** | **`uxcompose`** |

## From this source tree (0.2.0)

```bash
cd <checkout>
pip install -e ".[fastapi]"
```

Published form (when uploaded):

```bash
pip install 'ux-dom[fastapi]'
```

## Extras

| Extra | Provides |
|-------|----------|
| **`fastapi`** | fastapi, which brings Starlette: imported by `ux_dom.response.starlette`, and by `install_safe_static` when called |

Extras carry only packages `src/ux_dom` imports
([ADR 0003](adr/0003-layer-boundary.md) rule 2). There is no `dev`, `fastapidev`,
`tailwind` or `hmr` extra. An ASGI server (uvicorn) comes with ux-compose. Product CSS
compile is `uxcompose build`. Product HMR is `uxcompose serve dev`.

## CLI

```bash
# Product apps (composition + delivery):
uxcompose create-app myapp
uxcompose build
uxcompose serve dev app:asgi --port 8080

# Pure Document tooling:
uxdom --help
uxdom doctor
uxdom lint
```

## Import

```python
from ux_dom import Document, Component
from ux_dom import XElement, Csp
```

## Verify

```bash
python -c "import ux_dom; print(ux_dom.__version__)"
uxdom doctor
```
