# ux-dom examples

> For a new product app with file-based routing, start with
> **`uxcompose create-app myapp`** (ux-compose). These examples show
> **ux-dom on its own**, with explicit FastAPI routes. See
> [DX.md](../docs/guides/DX.md).

Every example is a package under `examples/`, run from the repository root:

```bash
poetry install --with dev            # or: pip install -e ".[fastapi]"
uvicorn examples.showcase.main:app --reload
```

| Example | Run | Shows |
|---------|-----|-------|
| [`showcase`](showcase/) | `examples.showcase.main:app` | Multi-page app: `Document` + `Htmx` + `Csp.auto()`, `defHTML`, Markdown, `Markup`, htmx partials, SSE, streaming |
| [`xelement_kit`](xelement_kit/) | `examples.xelement_kit.main:app` | `XElement` runtime: light/shadow DOM, slots, htmx re-upgrade, Alpine |
| [`ux_kit`](ux_kit/) | `examples.ux_kit.main:app` | `ux_dom.ui` component gallery, state as render arguments |
| [`ux_channel_counter`](ux_channel_counter/) | `examples.ux_channel_counter.main:app` | ux-dom document + ux-channel actions (`ch.control` / `ControlAttrs`, regions) |
| [`standalone`](standalone/) | `examples.standalone.<sse\|ws\|mcp\|search>:app` | One file per transport |

## The pattern every example follows

```python
from ux_dom import Document
from ux_dom.runtime import Csp, Htmx
from ux_dom.response.fastapi import HTMLRoute

document = Document(head=[...]).use(Htmx(version="2.0.4"), Csp.auto())

pages = APIRouter(route_class=HTMLRoute)     # endpoints return ux-dom trees
pages.add_api_route("/", home)               # explicit route table
app.include_router(pages)
document.mount(app)                          # runtime middleware + static files
```

* **Content safety.** Plain `str` is escaped. HTML you did not write goes
  through `defHTML` (allow-list sanitizer) or `MarkdownElement`. HTML you did
  write is marked with `markupsafe.Markup` and returned from a component's
  `render`.
* **htmx URLs are same-origin.** `hx-*`, `sse-connect` and `ws-connect` must
  point at your origin; wrap another origin in `ux_dom.dom.cross_origin(url)`.
* **Scripts.** Runtime scripts are pinned with SRI. Under `Csp`, scripts in
  the Document head/body get a nonce; page content must not contain inline
  scripts, so client code lives in static files.
* **CSP and CDNs.** `xelement_kit` and `ux_kit` use Alpine and/or the Tailwind
  play CDN, which do not work under a strict CSP, so they leave `Csp` out and
  say so. `showcase`, `ux_channel_counter` and `standalone` run under it.

## Capability matrix

| Capability | showcase | xelement_kit | ux_kit | ux_channel_counter | standalone |
|------------|:---:|:---:|:---:|:---:|:---:|
| `Document` runtimes, explicit routes | ✓ | ✓ | ✓ | ✓ | ✓ |
| `Csp.auto()` | ✓ | | | ✓ | ✓ |
| htmx partials | ✓ | ✓ | ✓ | | ✓ (search, mcp) |
| SSE | ✓ | | | | ✓ (sse) |
| WebSocket | | | | | ✓ (ws, mcp) |
| `StreamingRoute` | ✓ | | | | ✓ (search) |
| Custom elements (`XElement`) | | ✓ | | | |
| ux-channel actions | | | | ✓ | |

State in these demos (cart, guestbook, counters) is process memory: one
worker only. Use a database or Redis in production.

## Tests

```bash
python -m pytest tests/09_examples -q                 # HTTP-level, every example
python -m pytest tests/06_browser -q                  # Playwright (needs tests/browser deps)
```
