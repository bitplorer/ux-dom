# UxDom production examples

> Prefer **`uxcompose create-app myapp`** for greenfield product apps.
> These folders are **ux-dom-only render demos**, not the product routing path.
> See [DX.md](../docs/guides/DX.md).

Runnable, production-shaped apps demonstrating **ux_dom alone**.
ux_dom + ux-channel examples live in ux-channel (`python/examples/canonical_ux_dom`),
which owns that API.

## Layout

| App | Path | Stack | Port |
|-----|------|-------|------|
| Realtime kit | [`ux_dom_only/realtime_kit`](ux_dom_only/realtime_kit/) | SSE, WebSocketAdapter, streaming HTML | 8092 |
| **Showcase** | [`showcase`](showcase/) | ux_dom-only full demo (shop, cart, guestbook, SSE, stream) | 8000 |
| XElement kit | [`xelement_kit`](xelement_kit/) | Light/Shadow DOM, HTMX, Alpine, slots | 8080 |
| UI kit gallery | [`ux_kit`](ux_kit/) | `ux_dom.ui` components | 8080 |

## Capability matrix

| Capability | realtime_kit | showcase |
|------------|:---:|:---:|
| Components / Document | ✓ | ✓ |
| Explicit FastAPI routes (`StreamingRoute`) | | ✓ |
| HTMX partials / middleware | ✓ | ✓ |
| SSE | ✓ | ✓ |
| WebSocket (ux_dom adapter) | ✓ | |
| StreamingResponse | ✓ | ✓ |

Page routing (`routes/` folders) belongs to ux-compose; these demos register
routes explicitly.

## Run

```bash
# from repo root
export PYTHONPATH=.

# ux_dom only
uvicorn examples.ux_dom_only.realtime_kit.app:app --host 0.0.0.0 --port 8092

```

### Production notes

* Showcase cart store is process-local demo state — replace with DB for real deploys.
* Single-worker memory stores are intentional for demos (`allow_memory_stores=True`).

## Tests

```bash
python -m pytest tests/04_production/test_examples_production.py -q
```

### XElement kit (HTMX / Alpine / Web Components)

See [`xelement_kit/`](xelement_kit/).

- Light/Shadow full guides: [`xelement_kit`](xelement_kit/) ·
  [`docs/reference/XELEMENT.md`](../docs/reference/XELEMENT.md) ·
  [`docs/reference/HYPERMEDIA.md`](../docs/reference/HYPERMEDIA.md)

### ux_kit

Shadcn-inspired `ux_dom.ui` gallery (+ optional channel bridge). See
[docs/reference/UI.md](../docs/reference/UI.md).
