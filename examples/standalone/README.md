# Standalone apps

One file per transport. Each module has `create_app()` and a module-level
`app`; run any of them from the repository root:

```bash
uvicorn examples.standalone.sse:app --reload
```

| Module | Shows |
|--------|-------|
| `sse.py` | htmx SSE extension (`Htmx(sse=True)`); events carry rendered ux-dom fragments |
| `ws.py` | `WebSocketAdapter` with per-connection state; client in `static/ws_counter.js` (file, so the nonce CSP allows it) |
| `mcp.py` | MCP-style `tools/list` / `tools/call` (JSON-RPC 2.0 shape) over HTTP and WebSocket; results include escaped HTML; htmx form on `/` |
| `search.py` | One endpoint, two answers: fragment for htmx (`request.state.htmx`), full page otherwise; `StreamingRoute` |

Every page is a `Document` with `Csp.auto()`; pages that use htmx add the
pinned `Htmx` runtime. Tests: `tests/08_examples/test_standalone.py`.
