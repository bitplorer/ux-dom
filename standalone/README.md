# Standalone real-world apps

| App | Path | Surfaces |
|-----|------|----------|
| SSE ticker | `sse_app/` | `sse_*` attrs, `text/event-stream`, HTML stream |
| WS counter | `ws_app/` | `WebSocketAdapter`, per-conn isolation, events |
| MCP tools | `mcp_app/` | tools/list, tools/call (HTTP + WS), ux_dom HTML results |
| HTMX stream | `htmx_stream_app/` | HX partials, StreamingResponse, route `get`/`search` |

Run production tests:

```bash
python -m pytest tests/04_production/test_standalone_apps_production.py -q
```
