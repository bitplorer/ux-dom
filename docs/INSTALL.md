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
| **`fastapi`** | fastapi, uvicorn, python-multipart |
| **`fastapidev`** | Dev-oriented FastAPI stack + pytailwindcss |
| **`dev`** | pytailwindcss, uvicorn |

There is no `tailwind` or `hmr` extra. Product CSS compile is
`uxcompose build`. Product HMR is `uxcompose serve dev`.

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
from ux_dom.runtime import XElement, Htmx, Csp
```

## Verify

```bash
python -c "import ux_dom; print(ux_dom.__version__)"
uxdom doctor
```
