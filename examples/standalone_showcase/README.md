# UxDom Standalone Showcase

A **production-shaped** example app using only **UxDom + FastAPI** (no ux-channel).

## Features

| Feature | Where |
|---------|--------|
| Components + Document | `app/routes/*`, `app/document.py` |
| File routes (leftover standalone demo) | `app/routes/` — product apps use ux-compose |
| HTMX partials | `POST /cart/Cart` swaps `#cart-root` |
| SSE | `GET /api/sse` + page `/sse/SseDemo` |
| Streaming HTML | `GET /api/stream` |

## Run

From this directory:

```bash
pip install -r requirements.txt
# from ux_dom repo with local package:
#   PYTHONPATH=../.. pip install -e ../..
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

From the **ux_dom** repo root:

```bash
PYTHONPATH=examples/standalone_showcase:./ \
  uvicorn app.main:app --app-dir examples/standalone_showcase \
  --host 0.0.0.0 --port 8080 --reload
```

Or:

```bash
cd examples/standalone_showcase
PYTHONPATH=../..:. uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

Open http://127.0.0.1:8080/

## Routes

| Path | Description |
|------|-------------|
| `/` | → home |
| `/index/Index` | Feature tour |
| `/shop/Shop` | Catalog |
| `/cart/Cart` | HTMX cart (GET page, POST partial) |
| `/sse/SseDemo` | Live SSE UI |
| `/stream/StreamDemo` | Stream docs |
| `/api/sse?n=5` | Finite SSE for tests |
| `/api/stream` | StreamingResponse fragment |
| `/health` | JSON health |

## Scaffold origin

Historical demo tree (pre product-CLI hard cut). Product apps: `uxcompose create-app`.
