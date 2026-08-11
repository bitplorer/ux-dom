"""Minimal MCP-inspired tools server: tools/list + tools/call → ux_dom HTML fragments.

Not full MCP wire protocol; models the Intent→Action→Result pattern with
JSON-RPC shaped messages and HTML tool results for hypermedia UIs.
"""
from __future__ import annotations

import json
from typing import Any

from fastapi import FastAPI, Request, WebSocket
from fastapi.responses import JSONResponse

from ux_dom import Component
from ux_dom.dom import div, span, ul, li, h2
from ux_dom.htmx.middleware import HtmxMiddleware
from ux_dom.response.starlette import HTMLResponse


class ToolResult(Component):
    def render(self, name: str = "", result: str = "", ok: bool = True):
        return div(
            span(name, id="tool-name"),
            span("ok" if ok else "err", id="tool-status"),
            span(result, id="tool-result"),
            id="tool-out",
            data_ok=str(ok).lower(),
        )


class ToolCatalog(Component):
    def render(self, tools: list | None = None):
        tools = tools or []
        return div(
            h2("Tools"),
            ul(*[li(t["name"], id=f"tool-{t['name']}") for t in tools]),
            id="catalog",
        )


TOOLS = {
    "echo": {
        "name": "echo",
        "description": "Echo a string",
        "inputSchema": {"type": "object", "properties": {"text": {"type": "string"}}},
    },
    "add": {
        "name": "add",
        "description": "Add two numbers",
        "inputSchema": {
            "type": "object",
            "properties": {"a": {"type": "number"}, "b": {"type": "number"}},
        },
    },
    "render_card": {
        "name": "render_card",
        "description": "Return a ux_dom HTML card",
        "inputSchema": {"type": "object", "properties": {"title": {"type": "string"}}},
    },
}


def run_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    if name not in TOOLS:
        return {"ok": False, "error": f"unknown tool {name}", "html": ""}
    if name == "echo":
        text = str(arguments.get("text", ""))
        html = ToolResult(name=name, result=text, ok=True).__render__(pretty=False)
        return {"ok": True, "result": text, "html": html}
    if name == "add":
        a = float(arguments.get("a", 0))
        b = float(arguments.get("b", 0))
        s = a + b
        html = ToolResult(name=name, result=str(s), ok=True).__render__(pretty=False)
        return {"ok": True, "result": s, "html": html}
    if name == "render_card":
        title = str(arguments.get("title", "Card"))
        from ux_dom.dom import div as d

        card = d(title, id="card", className="card")
        html = card.__render__(pretty=False)
        return {"ok": True, "result": title, "html": html}
    return {"ok": False, "error": "unhandled", "html": ""}


def create_app() -> FastAPI:
    app = FastAPI(title="ux_dom-mcp")
    app.add_middleware(HtmxMiddleware)

    @app.get("/")
    def home():
        return HTMLResponse(ToolCatalog(tools=list(TOOLS.values())))

    @app.get("/mcp/tools/list")
    def tools_list():
        return {"tools": list(TOOLS.values())}

    @app.post("/mcp/tools/call")
    async def tools_call(request: Request):
        body = await request.json()
        # JSON-RPC-ish or plain
        if "method" in body:
            if body["method"] != "tools/call":
                return JSONResponse(
                    {"error": f"unknown method {body['method']}"}, status_code=400
                )
            params = body.get("params") or {}
            name = params.get("name")
            arguments = params.get("arguments") or {}
            req_id = body.get("id")
            out = run_tool(name, arguments)
            return {"jsonrpc": "2.0", "id": req_id, "result": out}
        name = body.get("name")
        arguments = body.get("arguments") or {}
        return run_tool(name, arguments)

    @app.get("/mcp/tools/call/html")
    def tools_call_html(name: str, **kwargs):
        # query-style for HTMX
        args = {k: v for k, v in kwargs.items()}
        out = run_tool(name, args)
        if not out["ok"]:
            return HTMLResponse(ToolResult(name=name, result=out.get("error", ""), ok=False))
        # parse html back is hard — re-render
        return HTMLResponse(ToolResult(name=name, result=str(out.get("result", "")), ok=True))

    @app.websocket("/mcp/ws")
    async def mcp_ws(websocket: WebSocket):
        await websocket.accept()
        try:
            while True:
                raw = await websocket.receive_text()
                try:
                    msg = json.loads(raw)
                except json.JSONDecodeError:
                    await websocket.send_json({"error": "invalid json"})
                    continue
                method = msg.get("method")
                req_id = msg.get("id")
                if method == "tools/list":
                    await websocket.send_json(
                        {"jsonrpc": "2.0", "id": req_id, "result": {"tools": list(TOOLS.values())}}
                    )
                elif method == "tools/call":
                    params = msg.get("params") or {}
                    out = run_tool(params.get("name"), params.get("arguments") or {})
                    await websocket.send_json(
                        {"jsonrpc": "2.0", "id": req_id, "result": out}
                    )
                else:
                    await websocket.send_json(
                        {"jsonrpc": "2.0", "id": req_id, "error": {"message": "unknown method"}}
                    )
        except Exception:
            try:
                await websocket.close()
            except Exception:
                pass

    @app.get("/health")
    def health():
        return {"ok": True, "tools": list(TOOLS)}

    return app


app = create_app()
