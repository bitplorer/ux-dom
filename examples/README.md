# UxDom production examples

> Prefer **`uxdom create-app myapp`** for greenfield projects (Tailwind, HTMX, optional ux-channel).

Runnable, production-shaped apps demonstrating **ux_dom alone** and **ux_dom + ux-channel**.

## Layout

| App | Path | Stack | Port |
|-----|------|-------|------|
| Hypermedia shop | [`ux_dom_only/hypermedia_shop`](ux_dom_only/hypermedia_shop/) | uxdom plugins, DirectoryRouter, HTMX | 8091 |
| Realtime kit | [`ux_dom_only/realtime_kit`](ux_dom_only/realtime_kit/) | SSE, WebSocketAdapter, streaming HTML | 8092 |
| Live cart | [`with_ux_channel/live_cart`](with_ux_channel/live_cart/) | ux_dom markup + Channel regions/actions | 8093 |
| **Standalone showcase** | [`standalone_showcase`](standalone_showcase/) | ux_dom-only full demo (shop, HTMX, SSE, stream) | 8080 |
| Market board | [`with_ux_channel/market_board`](with_ux_channel/market_board/) | live.bind/publish + UxDom shell | 8094 |

## Capability matrix

| Capability | hypermedia_shop | realtime_kit | live_cart | market_board |
|------------|:---:|:---:|:---:|:---:|
| Components / Document | ✓ | ✓ | ✓ | ✓ |
| DirectoryRouter `[id]` | ✓ | | | |
| Route classmethods + DOM API | ✓ | | | |
| HTMX partials / middleware | ✓ | ✓ | | |
| SSE | | ✓ | | via channel push |
| WebSocket (ux_dom adapter) | | ✓ | | |
| StreamingResponse | | ✓ | | |
| uxchannel Region | | | ✓ | ✓ |
| `ch.control(...).as_ux_dom()` | | | ✓ | ✓ |
| Trust caps / morph client | | | ✓ | ✓ |
| `ch.live` topics | | | | ✓ |

## Run

```bash
# from repo root (ux_dom-improve)
export PYTHONPATH=.

# ux_dom only
uvicorn examples.ux_dom_only.hypermedia_shop.app:app --host 0.0.0.0 --port 8091
uvicorn examples.ux_dom_only.realtime_kit.app:app --host 0.0.0.0 --port 8092

# with uxchannel (install companion package first)
pip install -e /path/to/uxchannel # or: pip install ux-channel uvicorn examples.with_ux_channel.live_cart.app:app --host 0.0.0.0 --port 8093
uvicorn examples.with_ux_channel.market_board.app:app --host 0.0.0.0 --port 8094
```

### Production notes

* Set `UID_CHANNEL_SECRET` (≥32 chars) for channel apps.
* Multi-worker channel: set `REDIS_URL` (uses `ChannelConfig.production(...).with_redis`).
* Shop cart store is process-local demo state — replace with DB for real deploys.
* Single-worker memory stores are intentional for demos (`allow_memory_stores=True`).

## Tests

```bash
python -m pytest tests/test_examples_production.py -q
```

### XElement kit (HTMX / Alpine / Web Components)

See [`xelement_kit/`](xelement_kit/).

- Light/Shadow full guides: [`xelement_kit`](xelement_kit/) · [`docs/XELEMENT.md`](../docs/XELEMENT.md)

### ux_kit

Shadcn-inspired `ux_dom.ui` gallery (+ optional channel bridge). See docs/UI.md.
