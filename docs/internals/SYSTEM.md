# ux-dom System Boundary (residual-free)

> Companion to ux-compose `docs/FLOW.md`. Start there for the full stack.

---

## One rule

**ux-dom renders. It does not own product delivery.**

```text
IN  → tag trees / Document / pure discovery
OUT → HTML string | bytes | async token stream  (+ Document shell meaning)
```

Everything after that (HTTP boxes on an ASGI app, host choice, HMR process,
product scaffold, channel) is **ux-compose**.

---

## Owns

| Concern | Location |
|---------|----------|
| Tag tree, Component | `dom/` |
| `__render__` / `__async_render__` | `dom_tag` (serialize SSoT) |
| Pure body helpers (no FastAPI) | optional helpers calling dunders |
| Document shell | Document + contributions |
| control dialect | via `Document.use` |
| runtime script tags | via `Document.use` |
| **CSP stamp + policy** | via `Document.use` |
| style tags/href | style contributions |
| Pure page discovery | `routing/core` DirectoryRoutes + RouterHooks |

---

## Does **not** own (product path)

| Concern | Correct home |
|---------|----------------|
| Product HTTP delivery story | ux-compose |
| Host strategy / which ASGI app | ux-compose Invisible |
| HMR watch + WebSocket | ux-compose (dev) |
| Product `create-app` | **`uxcompose create-app` only** |
| Second product App (`plugins.App.web`) | Forbidden as product path |
| Channel / Intent transport | ux-compose `wire/` |

Thin FastAPI helpers that may still exist in-tree are **not** the product
narrative. Product authors use ux-compose.

---

## Document.use

Allowed: control, runtime tags, CSP, style tags.

**Not** a product API for HMR process or FastAPIHost app assembly.

---

## Scaffold

| CLI | Role |
|-----|------|
| `uxcompose create-app` | **Sole product scaffold** |
| `uxdom create-app` | Not promoted for product apps |

---

## Forbidden residuals

- Recommending `ux_dom.plugins.App.web` as the app entry
- Treating HMR as a Document.use requirement
- Moving CSP **stamp** ownership to a FastAPI host package
- Importing FastAPI inside serialize/dunder path

---

See ux-compose `docs/FLOW.md` for end-to-end mount, channel, and HMR flows.
