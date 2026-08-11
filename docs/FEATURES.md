# ux-dom 0.1 — Feature encyclopedia

**Status:** complete product map for **0.1** (sandbox — no legacy/shim surface)  
**Brand:** PyPI `ux-dom` · import `ux_dom` · CLI **`uxdom`**  
**Core loop:** **Document → Component tree → HTML** (+ optional HTMX / Alpine / XElement / channel runtime)

This document catalogs **every major feature**: what it is, when to use it,
public API, implementation paths, configuration, tests, and deep docs.
If something is missing, treat it as undocumented and update this file with the code.

Related stack peer: **ux-channel** (optional control plane) — see [STACK.md](STACK.md).

---

## How to read this document

| Column | Meaning |
|--------|---------|
| **Use when** | Product situations that justify the feature |
| **API** | Stable imports / entry points |
| **Implements** | Paths under `ux_dom/` |
| **Config** | Settings / env / Document options |
| **Tests** | Primary suites under `tests/` |
| **Docs** | Deep guides |

**Day-1 path:** [START_HERE.md](START_HERE.md) + Document + tags + optional XElement/Htmx.

---

## 0. Product identity

| Item | Value |
|------|--------|
| Version | **0.1.0** (`ux_dom.__version__`) |
| License | MIT |
| Python | See `pyproject.toml` (modern CPython) |
| Peer | Optional **ux-channel** for Intent→Result control (not required) |
| Host | FastAPI / Starlette ASGI first-class |

```python
from fastapi import FastAPI
from ux_dom import Document, Component, ReactiveComponent
from ux_dom.runtime import XElement, Htmx, Csp
from ux_dom.dom import div, h1

document = Document(head=[], body=[]).use(XElement(), Htmx(), Csp.auto())
app = FastAPI(title="App")
document.mount(app)
```

---

## 1. Document shell (SSoT)

### 1.1 Document

| | |
|--|--|
| **What** | HTML document SSoT: head/body, `.use(runtimes)`, `.mount(app)`, render entry |
| **Use when** | Every app — single shell for pages and assets |
| **API** | `Document` (from `ux_dom` / `ux_dom.settings`) |
| **Implements** | `settings/document.py`, `settings/paths.py`, `settings/commands.py` |
| **Config** | `ensure_csrf_token`, asset paths, tailwind commands, head/body stages |
| **Tests** | `tests/` document & settings suites |
| **Docs** | [DOCUMENT](guides/DOCUMENT.md) · [DOCUMENT_TWO_STAGE](guides/DOCUMENT_TWO_STAGE.md) · [DOCUMENT_AND_APP](guides/DOCUMENT_AND_APP.md) |

```python
document = Document(head=[], body=[], ensure_csrf_token=False).use(...)
document.mount(app)
return document(div(...), page_title="Home")
```

### 1.2 Web assets & paths

| | |
|--|--|
| **What** | Static asset resolution, package static, safe static serving |
| **API** | `WebAssets`, path helpers in settings |
| **Implements** | `settings/paths.py`, `plugins/package_static.py`, `plugins/safe_static.py` |
| **Docs** | INSTALL · DOCUMENT |

### 1.3 Tailwind / style commands

| | |
|--|--|
| **What** | Optional Tailwind integration for DX builds |
| **API** | Tailwind command helpers in settings |
| **Implements** | `settings/commands.py`, `plugins/style/` |
| **Docs** | CLI · DX |

---

## 2. Core components

### 2.1 Component & Fragment

| | |
|--|--|
| **What** | Composable HTML trees; Fragment for multi-root |
| **Use when** | Any UI structure beyond raw tags |
| **API** | `Component`, `Fragment`, `MergeClassAttribute` |
| **Implements** | `dom/src/component.py` |
| **Docs** | [COMPONENTS](guides/COMPONENTS.md) · [CORE](internals/CORE.md) |

### 2.2 ReactiveComponent

| | |
|--|--|
| **What** | Components with reactive state / re-render semantics |
| **Use when** | Live updating islands within SSR HTML |
| **API** | `ReactiveComponent` |
| **Implements** | `dom/src/component.py` (reactive path) |
| **Tests** | reactive / stress suites under `tests/` |
| **Docs** | [REACTIVE](guides/REACTIVE.md) |

### 2.3 Render phases & concurrency

| | |
|--|--|
| **What** | Sync/async render consistency; tree safety under load |
| **Implements** | component render path, `concurrency.py` |
| **Docs** | [RENDER_PHASES](internals/RENDER_PHASES.md) · [CONCURRENCY](internals/CONCURRENCY.md) · [CONTEXT_SYNC_ASYNC](internals/CONTEXT_SYNC_ASYNC.md) |

---

## 3. DOM layer

### 3.1 HTML / SVG tags

| | |
|--|--|
| **What** | Full tag functions (`div`, `span`, `input`, SVG, …) |
| **Use when** | Building trees in Python |
| **API** | `from ux_dom.dom import div, h1, …` · `ux_dom.dom` |
| **Implements** | `dom/src/htmltags.py`, `dom/src/svgtags.py`, `dom/htmlelement.py` |
| **Docs** | [HYPERMEDIA](guides/HYPERMEDIA.md) · MODULE_MAP |

### 3.2 Parse / serialize / document helpers

| | |
|--|--|
| **What** | HTML document helpers, element model, pretty stream |
| **Implements** | `dom/htmldocument.py`, `dom/ui.py`, serialize paths |
| **Docs** | [PRETTY_STREAM](internals/PRETTY_STREAM.md) |

### 3.3 Unique IDs

| | |
|--|--|
| **What** | Stable unique id generation for elements |
| **Implements** | `dom/uniqueid.py` |

### 3.4 Icons & Jinja bridge

| | |
|--|--|
| **What** | Icon helpers; optional Jinja integration |
| **Implements** | `dom/icons.py`, `dom/jinja.py` |

---

## 4. Runtime plugins (Document.use)

### 4.1 XElement (Web Components)

| | |
|--|--|
| **What** | Custom elements runtime + `x_element.js` served from package |
| **Use when** | Encapsulated client behavior, custom elements, auto definitions |
| **API** | `ux_dom.runtime.XElement`, `XElementRuntime` |
| **Implements** | `runtime/` (exports), plugins runtime, static JS assets |
| **Static** | `XELEMENT_JS_URL`, `XELEMENT_STATIC_PREFIX` — sourced from package, not a hand-copied dead path |
| **Docs** | [XELEMENT](guides/XELEMENT.md) · [XELEMENT_AUTO_DEFINITIONS](guides/XELEMENT_AUTO_DEFINITIONS.md) |

### 4.2 HTMX

| | |
|--|--|
| **What** | HTMX runtime wiring for hypermedia partials |
| **API** | `Htmx`, `HtmxControl` |
| **Implements** | runtime + htmx package integration |
| **Docs** | [HYPERMEDIA](guides/HYPERMEDIA.md) |

### 4.3 Alpine.js

| | |
|--|--|
| **What** | Alpine runtime integration |
| **Implements** | `alpinejs/` |
| **Docs** | HYPERMEDIA · COOKBOOK |

### 4.4 CSP (Content Security Policy)

| | |
|--|--|
| **What** | CSP middleware/policy builder (`Csp.auto()`, nonces, strict-dynamic) |
| **Use when** | Production browser security |
| **API** | `Csp`, `CspMiddleware` |
| **Implements** | `plugins/csp.py` |
| **Docs** | [CSP](security/CSP.md) |

### 4.5 Channel runtime (optional ux-channel peer)

| | |
|--|--|
| **What** | Wire Document to ux-channel client control plane |
| **Use when** | Intent→Result ops + regions with ux-dom markup |
| **API** | `Channel`, `UxChannelRuntime` from `ux_dom.runtime` |
| **Docs** | [STACK](STACK.md) · channel FEATURES in peer repo |

---

## 5. Plugins hub & host

| Feature | Role | Implements | Docs |
|---------|------|------------|------|
| **Hub** | Plugin contribution registry | `plugins/hub.py`, `contribution.py` | ARCHITECTURE |
| **Host** | ASGI host integration | `plugins/host/` | DOCUMENT_AND_APP |
| **Shell** | Shell composition | `plugins/shell.py` | DOCUMENT |
| **Dedupe** | Asset/runtime dedupe | `plugins/dedupe.py` | internals |
| **HMR** | Hot reload helpers | `plugins/hmr/` | DX |
| **Control** | Control-plane plugin hooks | `plugins/control/` | STACK |
| **Routing plugin** | Route contribution | `plugins/routing/` | ROUTING |
| **Response plugin** | Response adapters | `plugins/response/` | — |
| **Style** | CSS/Tailwind pipeline | `plugins/style/` | CLI |

---

## 6. Routing & response

### 6.1 Directory / FastAPI routing

| | |
|--|--|
| **What** | File/directory-oriented routes, streaming routes |
| **API** | `ux_dom.routing` (FastAPI helpers) |
| **Implements** | `routing/fastapi.py` |
| **Docs** | [ROUTING](guides/ROUTING.md) |

### 6.2 Response adapters

| | |
|--|--|
| **What** | HTML / streaming responses for Starlette |
| **API** | `ux_dom.response` |
| **Implements** | `response/starlette.py` |
| **Docs** | ROUTING · HYPERMEDIA |

---

## 7. Slots & web components

| | |
|--|--|
| **What** | Slot model for composition and custom element slots |
| **API** | `Slots`, `WebComponentSlot`, custom element slot helpers |
| **Implements** | `slots/slots.py`, `slots/web_component_slot.py`, `slots/custom_element_slot.py` |
| **Docs** | COMPONENTS · XELEMENT |

---

## 8. Form / typed elements

| | |
|--|--|
| **What** | Typed input helpers (bools, buttons, chars, dates, enums, floats, integers) |
| **Use when** | Safer form controls than raw tags |
| **API** | `ux_dom.elements.*` |
| **Implements** | `elements/` |
| **Docs** | COOKBOOK · COMPONENTS |

---

## 9. Optional UI kit (`ux_dom.ui`)

| | |
|--|--|
| **What** | Copy-friendly shadcn-style primitives (button, card, dialog, table, …) |
| **Use when** | Fast product UI without inventing design tokens from scratch |
| **API** | `ux_dom.ui` (`button`, `card`, `dialog`, `input`, `table`, `tabs`, …) |
| **Implements** | `ui/*.py`, `ui/tokens.py`, `ui/catalog.py` |
| **Docs** | [UI](guides/UI.md) |

Includes `channel_bridge` helpers for channel-aware UI pieces when peer is present.

---

## 10. Web I/O protocol

| | |
|--|--|
| **What** | Internal web I/O adapter/events/protocol for streamy UI |
| **Implements** | `web_io/` (`_adapter`, `_events`, `_protocol`, `_types`) |
| **Docs** | internals · HYPERMEDIA |

---

## 11. CLI (`uxdom`)

| Command area | Role | Implements |
|--------------|------|------------|
| **create-app / scaffold** | New project | `cli/scaffold.py`, `cli/templates/`, `create/` |
| **doctor** | Environment diagnostics | `cli/doctor.py` |
| **build** | Production asset/build | `cli/build.py` |
| **lint** | Lint helpers | `cli/lint.py` |
| **profile** | Profiling DX | `cli/profile.py`, `profiling.py` |
| **dashboard** | DX dashboard | `cli/dashboard.py` |
| **deploy** | Deploy helpers | `cli/deploy.py` |
| **static assets** | Asset pipeline | `cli/static_assets.py` |
| **adders** | Add integrations | `cli/adders.py` |

```bash
uxdom create-app myapp
uxdom doctor
uxdom --help
```

**Docs:** [CLI](guides/CLI.md) · [DX](guides/DX.md)

---

## 12. Profiling & diagnostics

| | |
|--|--|
| **What** | cProfile / speedscope-oriented profiling; debug gallery |
| **API** | `ux_dom.profiling`, CLI profile |
| **Implements** | `profiling.py`, `diagnostics.py`, `debug_gallery.py` |
| **Docs** | DX · CONCURRENCY |

---

## 13. Reloader

| | |
|--|--|
| **What** | Dev reloader integration |
| **Implements** | `reloader/` |
| **Docs** | DX · TUTORIAL |

---

## 14. Security features

| Feature | Behavior | Docs |
|---------|----------|------|
| **CSP** | Nonce, strict-dynamic, host allowlists | [CSP](security/CSP.md) |
| **CSRF option** | `Document(ensure_csrf_token=…)` for host forms | DOCUMENT · security |
| **Safe static** | Controlled static file serving | plugins/safe_static |
| **HTML composition** | Server-owned markup reduces XSS surface vs ad-hoc strings | DESIGN_CANON |

---

## 15. Dependency runtime fix (`compat`)

| | |
|--|--|
| **What** | **Not** a public API shim. Runtime patch so optional **valio** works with PEP 649 annotation semantics on supported Pythons |
| **API** | Applied automatically at `import ux_dom` — apps do not call this |
| **Implements** | `compat/valio_pep649.py` |
| **Note** | 0.1 sandbox: kept only as a **dependency interoperability** fix, not for renamed library APIs |

---

## 16. Concurrency & performance (cross-cutting)

| Feature | Default | Docs |
|---------|---------|------|
| Sync/async render parity | Required under race/load | CONCURRENCY · RENDER_PHASES |
| Tree mutation safety | Baked into component/render | MEMORY_TREE · CONCURRENCY |
| Profiling DX | Opt-in CLI/API | profiling.py |

---

## 17. Peer: ux-channel

| | |
|--|--|
| **What** | Optional Intent→Action→Result(ops) control plane |
| **Use when** | Caps, regions paint from server ops, bridges, agents |
| **DOM side** | `runtime.Channel` / `UxChannelRuntime`; UI `channel_bridge` |
| **Docs** | [STACK](STACK.md) · peer `docs/FEATURES.md` in ux-channel |

**Law:** ux-dom owns **markup**; ux-channel owns **control/trust/ops**.

---

## 18. Configuration summary

| Knob | Area |
|------|------|
| `Document(...)` kwargs | Shell, CSRF, head/body |
| `.use(XElement(), Htmx(), Csp.auto(), …)` | Runtimes |
| Settings paths / WebAssets | Static & build |
| CSP policy fields | security/CSP.md |
| CLI flags | `uxdom --help` |

Prefer Document + plugins over scattering globals.

---

## 19. Testing map

| Area | Typical path |
|------|----------------|
| Unit / components | `tests/` |
| Live browser | demosite / scripts + Playwright where present |
| Security CSP | tests + security docs |
| Concurrency / reactive | stress tests under `tests/` |

```bash
cd /path/to/ux-dom
pip install -e ".[fastapi]"
pytest -q
```

---

## 20. Use-case recipes

| You want… | Use |
|-----------|-----|
| First page | Document + `div`/`h1` + mount · START_HERE |
| SPA-like partials | Htmx + fragments · HYPERMEDIA |
| Custom elements | XElement + slots · XELEMENT |
| Reactive island | ReactiveComponent · REACTIVE |
| Design system speed | `ux_dom.ui` · UI |
| Strict CSP | `Csp.auto()` · CSP |
| File-based app | routing + scaffold · ROUTING · CLI |
| Channel ops + HTML | STACK + runtime.Channel |
| DX health | `uxdom doctor` · profiling |

---

## 21. Removed / non-goals in 0.1 sandbox

| Not in 0.1 product surface | Notes |
|----------------------------|--------|
| Legacy `uidom` / `UID_*` brand | Use `ux-dom` / `ux_dom` / `uxdom` |
| Migration shims from pre-0.1 names | Removed — sandbox clean break |
| Archive audit dumps as product docs | Historical only if present under archive (not required) |
| Mandatory ux-channel | Optional peer |
| Second design system as core | `ui/` is optional kit |

---

## 22. Documentation tree

```text
docs/
  FEATURES.md          ← this encyclopedia
  START_HERE.md · INSTALL.md · README.md · STACK.md
  guides/              tutorial, document, components, xelement, routing, UI, DX…
  internals/           architecture, render phases, concurrency, module map
  security/            CSP
  ship/                maintenance / ship notes
```

---

## 23. Source-of-truth rules

| Concern | Truth |
|---------|--------|
| Public day-1 imports | `ux_dom/__init__.py` + [API_SURFACE](guides/API_SURFACE.md) |
| Feature list | **This file** |
| Architecture | [ARCHITECTURE](internals/ARCHITECTURE.md) · [MODULE_MAP](internals/MODULE_MAP.md) |
| Version | `ux_dom/__init__.py` / `VERSION` / `pyproject.toml` |

**When you add a feature:** update code, tests, and **this encyclopedia**.

---

## 24. Quick import card

```python
from ux_dom import Document, Component, Fragment, ReactiveComponent
from ux_dom.dom import div, h1, form, input_, button
from ux_dom.runtime import XElement, Htmx, Csp, Channel
from ux_dom import ui  # optional kit
```

CLI: **`uxdom`**.
