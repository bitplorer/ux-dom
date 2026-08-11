# UxDom-only realtime kit

| Feature | Endpoint |
|---------|----------|
| SSE | `GET /api/sse/{topic}?n=5` |
| WebSocket counter | `WS /ws/counter` |
| Streaming HTML | `GET /stream` |
| Pages | `/`, `/sse`, `/ws-page` |

```bash
uvicorn examples.ux_dom_only.realtime_kit.app:app --host 0.0.0.0 --port 8092
```
