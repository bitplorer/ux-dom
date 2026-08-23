> Product entry: [START_HERE.md](../START_HERE.md)

# ux-dom Capabilities Checklist

Release gate: every row must stay true (for the 0.1 freeze).

Version: **0.1.0** (ux-dom production line).

## Markup (CORE)

- [x] `with` tree construction + `attr()` / `get_current()`
- [x] Task/context-local stack (asyncio-safe; no bare thread-only key)
- [x] Layered `clean_attribute`: L0 `dom_tag` / L1 `Tags` / L2 `StyleTags` (not a bug)
- [x] Boolean True/False/None + dict JSON attrs + multiline class collapse
- [x] `Component` transparent `_entry` + hash/eq rules
- [x] `Fragment` / `MergeClassAttribute` / Alpine `DataSet`
- [x] `ReactiveComponent` re-render
- [x] `HtmlDocument` placeholders + XTemplate/WC hoist
- [x] `__render__` / `__async_render__` / `async with` (`__aenter__` / `__aexit__`)
- [x] `uniqueid`, SVG tags, CSS tags, `defHTML` parse path
- [x] Top-level `from ux_dom import Component, Fragment, Document, WebAssets`

## Host / routing (HOST)

- [x] `StreamingRoute` + `HTMLRoute`
- [x] **`DirectoryRoutes`** + thin adapters (preferred product bind)
- [x] **`DirectoryRouter`** convenience batteries (standalone FastAPI only)
- [x] Component `routes = [...]` convention
- [x] Plugin wrapper `plugins.routing.DirectoryRouting` (non-product)
- [x] Static mount pattern preserved in experiment trees (tests)

## Control (CTRL)

- [x] HTMX attrs via Tags dialect (`hx_*`)
- [x] `HtmxControl` plugin: scripts, partial policy, optional middleware
- [x] `Htmx` decorator class + `HtmxMiddleware` (module paths stable in 0.1)
- [x] `data-channel-*` attrs for ux-channel peer plane (no core import of channel)
- [x] `NullControl` for tests

## Infra

- [x] `WebAssets` / Dir family
- [x] `TailwindCommand.is_tailwindcss_available` → **bool** (fixed)
- [x] `async_run` watch mode **non-blocking** (fixed); `async_stop`
- [x] HotReloadWebSocketRoute API preserved
- [x] `x_element_js` + `x_element.js` (pairs with Python XElement / x-tagname) — see [XELEMENT.md](../guides/XELEMENT.md)

## Feature packs (optional import)

- [x] `ux_dom.elements` + valio
- [x] `ux_dom.alpinejs`
- [x] `ux_dom.slots`
- [x] Jinja / Markdown element paths

## Plugin system

- [x] `PluginHub` + `App.use(...)`
- [x] Protocols: host, routing, response, assets, style, hmr, control
- [x] Explicit registration only (no silent entry-point autoload by default)

## Known follow-ups (not regressions)

- [x] Walk-stream `__async_render__` (compact open→children→close; pretty uses full engine)
- [ ] watchfiles backend replace watchgod
- [ ] `ux_dom[channel]` ControlPlugin package
- [x] Product CLI moved: `uxcompose create-app | serve | deploy` (not uxdom)
- [x] Standalone Tailwind CLI resolver (`cli/tailwind.py`)
- [x] DirectoryRoutes `[id]` → `{id}` + private `_*.py` skip
- [x] FastAPIHost + DirectoryRouting + control/style/hmr plugins (quarantined, not product)


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
