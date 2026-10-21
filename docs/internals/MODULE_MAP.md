# Module map — every package area

Purpose of each tree under `ux_dom/`. Prefer this over guessing from file names.

## Design overview

```text
ux_dom/
  settings/     Document factory
  dom/          Tags, Component, serialize, XElement types
  plugins/      Document contributions (CSP, SafeStatic, hub)
  response/     HTML / streaming adapters
  scripts/      x_element.js (package-mounted)
  cli/          doctor, lint, profile, add, dashboard (pure-dom)
  ui/           Optional copy-in kit
```

Product scaffold + DirectoryRoutes is **uxcompose** ([DX.md](../guides/DX.md)).
This package does not ship `CreateProject`, `DirectoryRoutes`, `WebAssets`, or `TailwindCommand`.
ux-dom ships no file router (its routing module was removed, F-18).

| Path | Role | Public? |
|------|------|---------|
| `ux_dom/__init__.py` | Version + re-exports Document, Component, runtime facades | **Public** |
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
| **`ux_dom/settings/`** | Document | **Public** |
| **`ux_dom/plugins/`** | Hub, contributions, CSP, control, package static | Semi / **Public** facades |
| `ux_dom/plugins/runtime.py` | XElementRuntime, UxChannelRuntime — package static | Semi |
| `ux_dom/plugins/safe_static.py` | Allowlisted file mounts | Semi |
| **`ux_dom/response/`** | HTMLResponse, StreamingResponse | **Public** |
| **`ux_dom/scripts/`** | `x_element.js` + `x_element_js` embed helper | **Public** helper |
| **`ux_dom/cli/`** | Typer DX: doctor, lint, profile, add (not product scaffold) | CLI |
| **`ux_dom/ui/`** | Optional Tailwind UI kit (copy-in) | Optional public |
| **`ux_dom/slots/`** | Slot helpers for WebComponent | Semi |
| **`ux_dom/elements/`** | Typed form field components | Semi |
| **`ux_dom/alpinejs/`** | Opt-in Alpine attribute helpers (`DataSet`, `dataset_*`); not imported by `ux_dom` | Semi |

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
