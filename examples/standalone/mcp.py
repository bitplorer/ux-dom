"""MCP-style tool server whose tools return ux-dom HTML.

    uvicorn examples.standalone.mcp:app --reload        # from the repo root

Not the full MCP protocol: it models ``tools/list`` and ``tools/call`` with
JSON-RPC 2.0 shaped messages over HTTP and WebSocket. Every tool result
carries an ``html`` fragment rendered by ux-dom (user text escaped), so a
hypermedia UI can show it directly; ``/`` does that with htmx.
"""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse

from ux_dom import Component, Document
from ux_dom.dom import button, div, form, h1, h2, input_, li, meta, span, title, ul
from ux_dom.response.fastapi import HTMLRoute
from ux_dom.runtime import Csp, Htmx

# htmx would inject an inline <style> for .htmx-indicator; the nonce CSP
# blocks it, so turn that off (style indicators in your CSS instead).
HTMX_CONFIG = meta(name="htmx-config", content='{"includeIndicatorStyles":false}')

TOOLS: dict[str, dict[str, Any]] = {
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
        "description": "Return a ux-dom HTML card",
        "inputSchema": {"type": "object", "properties": {"title": {"type": "string"}}},
    },
}


class ToolResult(Component):
    def render(self, name: str, result: str, ok: bool = True):
        return div(
            span(name, id="tool-name"),
            span("ok" if ok else "error", id="tool-status"),
            span(result, id="tool-result"),
            id="tool-out",
            data_ok=str(ok).lower(),
        )


class Card(Component):
    def render(self, heading: str):
        return div(heading, id="card", className="card")


class ToolError(ValueError):
    """A tool was called with bad arguments."""


def _number(arguments: dict[str, Any], key: str) -> float:
    value = arguments.get(key, 0)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ToolError("a and b must be numbers")
    return value


def run_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Run one tool. Returns ``{"ok", "result", "html"}`` or ``{"ok": False, ...}``."""
    if name not in TOOLS:
        return {"ok": False, "error": f"unknown tool {name}", "html": ""}
    try:
        if name == "echo":
            result: Any = str(arguments.get("text", ""))
            html = str(ToolResult(name=name, result=result))
        elif name == "add":
            result = _number(arguments, "a") + _number(arguments, "b")
            html = str(ToolResult(name=name, result=str(result)))
        else:  # render_card
            result = str(arguments.get("title", "Card"))
            html = str(Card(heading=result))
    except ToolError as error:
        return {"ok": False, "error": str(error), "html": ""}
    return {"ok": True, "result": result, "html": html}


def rpc_result(req_id: Any, result: Any) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": req_id, "result": result}


def rpc_error(req_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}


def handle_rpc(message: dict[str, Any]) -> dict[str, Any]:
    req_id = message.get("id")
    method = message.get("method")
    params = message.get("params") or {}
    if method == "tools/list":
        return rpc_result(req_id, {"tools": list(TOOLS.values())})
    if method == "tools/call":
        return rpc_result(
            req_id, run_tool(params.get("name"), params.get("arguments") or {})
        )
    return rpc_error(req_id, -32601, f"unknown method {method}")


class Home(Component):
    def render(self):
        return div(
            h1("MCP-style tools"),
            h2("Tools"),
            ul(*[li(t["name"], id=f"tool-{t['name']}") for t in TOOLS.values()]),
            form(
                input_(name="text", placeholder="Text to echo", required=True),
                button("Call echo", type="submit"),
                hx_get="/mcp/tools/echo/html",
                hx_target="#tool-out",
                hx_swap="outerHTML",
            ),
            div(id="tool-out"),
            id="catalog",
        )


def create_app() -> FastAPI:
    document = Document(head=[HTMX_CONFIG]).use(Htmx(version="2.0.4"), Csp.auto())
    app = FastAPI(title="ux-dom MCP-style tools")

    def home():
        return document(Home(), head=[title("MCP-style tools")])

    def tools_list():
        return {"tools": list(TOOLS.values())}

    async def tools_call(request: Request):
        body = await request.json()
        if "method" not in body:  # plain {"name", "arguments"}
            return run_tool(body.get("name"), body.get("arguments") or {})
        reply = handle_rpc(body)
        return JSONResponse(reply, status_code=400 if "error" in reply else 200)

    def tool_html(name: str, request: Request):
        """htmx: run a tool with query-string arguments, return its fragment."""
        out = run_tool(name, dict(request.query_params))
        if not out["ok"]:
            return ToolResult(name=name, result=out["error"], ok=False)
        return ToolResult(name=name, result=str(out["result"]))

    async def tools_ws(websocket: WebSocket):
        await websocket.accept()
        try:
            while True:
                raw = await websocket.receive_text()
                try:
                    message = json.loads(raw)
                except json.JSONDecodeError:
                    await websocket.send_json(rpc_error(None, -32700, "parse error"))
                    continue
                await websocket.send_json(handle_rpc(message))
        except WebSocketDisconnect:
            pass  # the client left; nothing to clean up

    routes = APIRouter(route_class=HTMLRoute)
    routes.add_api_route("/", home)
    routes.add_api_route("/mcp/tools/list", tools_list)
    routes.add_api_route("/mcp/tools/call", tools_call, methods=["POST"])
    routes.add_api_route("/mcp/tools/{name}/html", tool_html)
    routes.add_api_route("/health", lambda: {"ok": True, "tools": list(TOOLS)})
    app.include_router(routes)
    app.add_api_websocket_route("/mcp/ws", tools_ws)
    document.mount(app)
    return app


app = create_app()
