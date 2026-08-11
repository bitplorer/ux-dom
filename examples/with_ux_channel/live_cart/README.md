# Live cart (ux_dom + ux-channel)

| Layer | Owns |
|-------|------|
| **ux_dom** | `Component`, `Document`, `button`/`div` trees, `data_channel_*` attrs via `as_ux_dom()` |
| **ux-channel** | `Channel.boot`, `Region`, `@ch.on`, trust caps, morph scripts, WS/SSE push hooks |

```bash
pip install ux-channel # or editable path to the companion package
uvicorn examples.with_ux_channel.live_cart.app:app --host 0.0.0.0 --port 8093
```

Optional multi-worker: set `REDIS_URL` and `UID_CHANNEL_SECRET` (≥32 chars).
