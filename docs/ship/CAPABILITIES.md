> Product entry: [START_HERE.md](../START_HERE.md)

# ux-dom Capabilities Checklist

Release gate: every row must stay true (for the 0.1 freeze).

Version: **0.1.0** (ux-dom production line).

## Markup (CORE)

- [x] `with` tree construction + `attr()` / `get_current()`
- [x] Task/context-local stack (asyncio-safe; no bare thread-only key)
- [x] Layered `clean_attribute`: L0 `dom_tag` / L1 `Tags` / L2 `StyleTags`
- [x] Boolean True/False/None + dict JSON attrs + multiline class collapse
- [x] `Component` transparent `_entry` + hash/eq rules
- [x] `Fragment` / `MergeClassAttribute` / Alpine `DataSet`
- [x] `ReactiveComponent` re-render
- [x] `HtmlDocument` placeholders + XTemplate/WC hoist
- [x] `__render__` / `__async_render__` / `async with` (`__aenter__` / `__aexit__`)
- [x] `uniqueid`, SVG tags, CSS tags, `defHTML` parse path
- [x] Top-level `from ux_dom import Component, Fragment, Document`

## Response

- [x] `StreamingRoute` + `HTMLRoute` (response adapters)
- [x] Component `routes = [...]` convention (when author wires explicitly)

## Control (CTRL)

- [x] HTMX attrs via Tags dialect (`hx_*`)
- [x] `HtmxControl` plugin: scripts, partial policy, optional middleware
- [x] `Htmx` decorator class + `HtmxMiddleware` (module paths stable in 0.1)
- [x] `data-channel-*` attrs for ux-channel peer plane (no core import of channel)
- [x] `NullControl` for tests

## Infra (render-only)

- [x] Package static: `/ux-dom/static/x_element.js`
- [x] `x_element_js` + `x_element.js` — see [XELEMENT.md](../guides/XELEMENT.md)
- [x] App folders / Tailwind CLI / product HMR → **ux-compose** (fail-closed here)

## Feature packs (optional import)

- [x] `ux_dom.elements` + valio
- [x] `ux_dom.alpinejs`
- [x] `ux_dom.slots`
- [x] Jinja / Markdown element paths

## Plugin system

- [x] `PluginHub` + Document `.use(...)`
- [x] Explicit registration only (no silent entry-point autoload by default)

## Product ownership (moved)

- [x] Product CLI: `uxcompose create-app | build | serve | deploy`
- [x] Product page routes: `ux_compose.routing.DirectoryRoutes`
- [x] CSS compiler: `uxcompose build` (`ux_compose.tailwind`)
- [x] App asset layout: `ux_compose.WebAssets`
- [x] Host strategy / HMR / tunnel: `uxcompose serve`

## Idempotency gates (0.1+)

- [x] `__render__` 3× identical (plain + control flags)
- [x] `_walk_render_tokens(pretty=False)` == `__render__(pretty=False)`
- [x] `__async_render__(pretty=False)` == compact `__render__`
- [x] StreamingResponse double-consume identical
- [x] HTTP GET same route twice → identical body
- [x] Concurrent `with` trees (80 tasks) isolated
- [x] `markdown=` does not poison process
- [x] CSRF policy per instance (no class race)

See `docs/ship/STABILITY.md` for last full audit.
