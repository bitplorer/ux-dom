# UxDom-only hypermedia shop

Production-shaped demo of **ux_dom without ux-channel**.

| Surface | Where |
|---------|--------|
| DirectoryRouter + `[id]` | `shop_routes/products/[id]/` |
| Component route classmethods | `CartCounter.get` / `.add` |
| DOM API unshadowed | instance `.get(id=…)` still works |
| HTMX partials | `hx_post` → fragment swap |
| Plugins | leftover `App` + `DirectoryRouting` + `HtmxControl` + `FastAPI()` |

```bash
uvicorn examples.ux_dom_only.hypermedia_shop.app:app --host 0.0.0.0 --port 8091
# open /shop/ or /health
```
