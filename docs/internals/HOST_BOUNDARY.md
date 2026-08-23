# Domain vs FastAPI host boundary (locked)

Library is not in production use. This document is the **hard** ownership contract —
not a deprecation plan. Dual paths are deleted or folded, not soft-warned.

---

## One sentence

**The tree serializes itself. The FastAPI host package turns that serialization into HTTP.**

---

## Layers

```text
┌─────────────────────────────────────────────────────────┐
│  DOMAIN (framework-free)                                │
│  dom tags · Document · Component                        │
│  __render__()        → full HTML str                    │
│  __async_render__()  → AsyncIterator[token]             │
│  DirectoryRoutes + RouterHooks → RouteRecords           │
│  Document.use(control / csp / runtime / style / hmr)    │
└──────────────────────────▲──────────────────────────────┘
                           │ tree | str | tokens | records
┌──────────────────────────┴──────────────────────────────┐
│  hosts.fastapi  (self-contained FastAPI delivery)       │
│  • HTMLResponse / StreamingResponse                     │
│      call dunders (+ optional CSP stamp)                │
│  • StreamingRoute / HTMLRoute                           │
│      endpoint return value → response class             │
│  • mount(records or DirectoryRoutes → include_router)   │
│  • DirectoryRouter batteries (standalone FastAPI only)  │
│  • optional thin app factory for pure-dom demos         │
└──────────────────────────▲──────────────────────────────┘
                           │ asgi_app =
┌──────────────────────────┴──────────────────────────────┐
│  ux-compose (only product author seat)                  │
│  App · mount · use_host (Invisible) · wire/             │
└─────────────────────────────────────────────────────────┘
```

---

## What a senior reader must conclude

| Question | Answer |
|----------|--------|
| Where is HTML produced? | `__render__` / `__async_render__` on the tree |
| Where is HTTP for FastAPI? | `ux_dom.hosts.fastapi` only |
| Is there a second body API? | **No** |
| Is `plugins.App` the product root? | **No** — `ux_compose.App` is |
| Does domain import FastAPI? | **No** |

If any of those answers is fuzzy, the boundary is broken.

---

## Package layout (target)

```text
ux_dom/
  dom/                     # tree model + dunders
  routing/core.py          # DirectoryRoutes, RouterHooks, records
  plugins/                 # Document contributions ONLY
    control/ csp runtime style hmr safe_static contribution hub

  hosts/
    fastapi/               # ALL FastAPI delivery — self-contained
      response.py          # HTMLResponse, StreamingResponse
      route.py             # StreamingRoute, HTMLRoute
      mount.py             # pure records → include_router
      directory.py         # DirectoryRouter batteries (standalone)
      app.py               # optional demo factory (not product root)
```

---

## Deleted concepts (not deprecated)

- Public product story for `prepare_html_body` / `prepare_html_stream`
  as “how body is made” (helpers may exist *inside* hosts.fastapi only)
- `plugins/host` as a parallel composition root
- `plugins.App.web()` as the recommended product path
- Dual “App” vocabulary for product authors

---

## Product path (only)

```python
from fastapi import FastAPI
from ux_compose import App

api = FastAPI()
app = App.boot("Shop")
app.mount(PACKAGE, asgi_app=api)   # compose Invisible → pure core + thin host
app.use_channel(asgi_app=api)
```

Page unit returns a tree (or unit that renders a tree).
Host package turns it into a streaming or full HTML response via dunders.

---

## Pure-dom / standalone FastAPI (no compose)

```python
from ux_dom.hosts.fastapi import StreamingResponse, StreamingRoute, DirectoryRouter
# still: body comes from tree.__async_render__ / __render__
```

---

Keep this file accurate. Any PR that puts FastAPI imports back into domain
serialize or invents a second body owner is out of contract.
