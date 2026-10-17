# UxDom Showcase

A small multi-page app built with ux-dom only: no JavaScript build step and no SPA.

```bash
# from the repository root
pip install -e ".[fastapi]"     # or: poetry install --with dev
uvicorn examples.showcase.main:app --reload
# open http://127.0.0.1:8000
```

| Page | File | Shows |
|------|------|-------|
| `/` | `pages/home.py` | One shared `Document`, a page title per page |
| `/shop` | `pages/shop.py` | CMS HTML through `defHTML` (allow-list sanitizer) |
| `/cart` | `pages/cart.py` | Form with `hx-post`; partial for htmx, 303 redirect without JS |
| `/guestbook` | `pages/guestbook.py` | User text escaped, Markdown via `MarkdownElement`, `javascript:` URLs made inert, trusted `Markup` from a component |
| `/sse` | `pages/live.py` | htmx SSE extension against `/api/sse` |
| `/stream` | `pages/live.py` | Page sent in chunks by `StreamingRoute` |

How it fits together:

* `document.py` builds the `Document` and adds the runtimes:
  `Htmx(version="2.0.4", sse=True, middleware=True)` (pinned scripts with SRI,
  `request.state.htmx`) and `Csp.auto()` (nonce CSP; dev or prod by `DEBUG`).
* `main.py` holds the explicit route table: `HTMLRoute` for pages,
  `StreamingRoute` for the streamed page, a plain router for JSON and SSE,
  then calls `document.mount(app)`.
* `static/app.css` is plain CSS, so the page runs under the strict CSP
  (no inline styles, no CSS CDN).
* htmx URLs are relative. ux-dom only lets `hx-*`, `sse-connect` and
  `ws-connect` point at the same origin; wrap another origin in
  `ux_dom.dom.cross_origin(url)` explicitly.

State (cart count, guestbook entries) is in process memory, for the demo only.

Tests: `tests/09_examples/test_showcase.py`.
