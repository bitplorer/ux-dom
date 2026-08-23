# Module map — every package area

Purpose of each tree under `ux_dom/`. Prefer this over guessing from file names.

## Design overview

```text
ux_dom/
  settings/     Document factory, WebAssets, paths
  dom/          Tags, Component, serialize, XElement types
  runtime/      Document-facing XElement / Htmx / Csp / Channel facades
  plugins/      Host, routing helper, CSP, SafeStatic, hub
  routing/      DirectoryRoutes (core) + adapters + DirectoryRouter batteries
  response/     HTML / streaming adapters
  scripts/      x_element.js (package-mounted)
  cli/          doctor, lint, build, profile, add, dashboard (pure-dom)
  ui/           Optional copy-in kit
```

Public apps compose **Document + DirectoryRoutes + thin adapter**. Product
scaffold is **uxcompose** ([DX.md](../guides/DX.md)).

| Path | Role | Public? |
|------|------|---------|
| `ux_dom/__init__.py` | Version + re-exports Document, Component, runtime facades | **Public** |
| `ux_dom/runtime/` | Stable aliases: `XElement`, `Htmx`, `Csp`, `Channel` | **Public** |
| `ux_dom/create/` | CreateAsgi (tests) · CreateProject.write() fails closed | Semi |
| `ux_dom/compat/` | Runtime compat (e.g. valio PEP 649) | Private |
| `ux_dom/diagnostics.py` | Error message builders for XElement checks | Private |
| **`ux_dom/dom/`** | Tag constructors, Document HTML helpers, parse | **Public** |
| `ux_dom/dom/htmlelement.py` | XElement / CustomElement / WebComponent / Alpine* | **Public** |
| `ux_dom/dom/htmldocument.py` | HtmlDocument + auto XElement definition collection | Semi |
| `ux_dom/dom/src/component.py` | Component, Fragment, ReactiveComponent | **Public** (via ux_dom) |
| `ux_dom/dom/src/dom_tag.py` | Tree node model, membership, `__render__` locks | Semi |
| `ux_dom/dom/src/dom1core.py` | DOM-like helpers (getElementById, …) | Semi |
| `ux_dom/dom/src/ext.py` | Tags serialize (pretty / walk / attr dialects) | Semi |
| `ux_dom/dom/src/concurrency.py` | Per-root tree locks | Private-ish |
| `ux_dom/dom/src/htmltags.py` / `csstags.py` / `jinjatags.py` / `svgtags.py` | Tag classes | via `ux_dom.dom` |
| `ux_dom/dom/src/html_string.py` | defHTML parse + sanitize | **Public** via dom |
| `ux_dom/dom/uniqueid.py` | Unique id generator for trees | Semi |
| `ux_dom/dom/src/ws_rpc.py` | Optional WS helpers (uses document.ux_domMessageHandler) | Advanced |
| **`ux_dom/settings/`** | Document, WebAssets, paths, TailwindCommand | **Public** |
| **`ux_dom/plugins/`** | Hub, contributions, host, routing, CSP, control | Semi / **Public** facades |
| `ux_dom/plugins/runtime.py` | XElementRuntime, UxChannelRuntime — package static | Semi |
| `ux_dom/plugins/safe_static.py` | Allowlisted file mounts | Semi |
| **`ux_dom/routing/`** | DirectoryRoutes + adapters; DirectoryRouter batteries | **Public** |
| **`ux_dom/response/`** | HTMLResponse, StreamingResponse | **Public** |
| **`ux_dom/scripts/`** | `x_element.js` + `x_element_js` embed helper | **Public** helper |
| **`ux_dom/cli/`** | Typer DX: doctor, lint, build, profile, add (not product scaffold) | CLI |
| **`ux_dom/ui/`** | Optional Tailwind UI kit (copy-in) | Optional public |
| **`ux_dom/slots/`** | Slot helpers for WebComponent | Semi |
| **`ux_dom/elements/`** | Typed form field components | Semi |
| **`ux_dom/htmx/`** | HTMX-oriented helpers | Semi |
| **`ux_dom/alpinejs/`** | Alpine sample widgets | Semi / demos |
| **`ux_dom/reloader/`** | Dev hot-reload WebSocket server bits | Dev |
| `ux_dom/web_io/` | Low-level web I/O helpers if present | Private |
| `ux_dom/assets/` | Thin facade over plugin hub static | Semi |

## Docs layout

| Dir | Audience |
|-----|----------|
| `docs/START_HERE.md` | Day-1 |
| `docs/guides/` | How to build apps |
| `docs/security/` | CSP, static, assets |
| `docs/internals/` | Design, modules, concurrency |
| `docs/ship/` | Deploy, stability, maintenance |
| `docs/archive/` | Historical notes (not current API) |

## Tests layout

| Dir | Focus |
|-----|--------|
| `tests/01_core` | DOM, Component, Tags, MRO, concurrency |
| `tests/02_document_plugins` | Document, CSP, plugins, XElement defs |
| `tests/03_routing_cli` | Router + DX CLI side-effect gates |
| `tests/04_production` | Readiness, showcase, typecheck |
| `tests/05_chaos` | Load, pen, enterprise battery |
| `tests/06_browser` | Playwright / live custom elements |
