# ux-dom design canon (0.1.0)

### Brand lines

| Layer | Name |
|-------|------|
| **PyPI / pip** | `ux-dom` |
| **Import** | `ux_dom` |
| **CLI** | **`uxdom`** |


---

## 1. Product intent

ux-dom is a **Python-first hypermedia UI stack**:

* Build HTML **as a tree of objects** (not templates-first).
* Ship **server-rendered HTML** that works with **HTMX / Alpine / custom elements**.
* Keep a **single Document shell** as SSoT for head/body and runtimes.
* Prefer **one copy** of library JS (from the installed package), not dual app copies.
* Prefer **CLI automation** for ceremonial app files (create-app / add) over
  hand-maintained boilerplate.

It is **not**: a React/Vue client framework, a multiplayer realtime mesh, or a second ASGI framework.

---

## 2. Ownership boundaries (non-negotiable)

| Owns | Does **not** own |
|------|------------------|
| **`Document`** — HTML shell, `.use()` runtimes, `.mount(app)` static + middleware | Routes, lifespan, process |
| **FastAPI / ASGI host** — routes, servers, app-level static | Head/body tag order |
| **`Component` / tags** — tree build + serialize | HTTP transport |
| **`XElementRuntime`** — serve `x_element.js` from package | App CSS / user assets |
| **`/assets`** (app) — Tailwind, images, app files | Library JS |

```text
Browser ──► /ux-dom/static/x_element.js  ──► site-packages/ux_dom/scripts/
Browser ──► /assets/*                       ──► project assets/
```

**Design choice:** dual-copy `assets/js/x_element.js` is **discouraged**. Default `serve="package_mount"`. Escape hatch `serve="webassets"` materializes a file for edge hosts only.

---

## 3. Tree model & render phases

Two different words that look alike:

| Phase | API | Meaning |
|-------|-----|---------|
| **Build** | `Component.__init__` / `render()` / `with div()` | Construct the in-memory tree |
| **Serialize** | `__render__` / `__async_render__` / `str()` / Response | Walk tree → HTML tokens |

See [RENDER_PHASES.md](RENDER_PHASES.md).

**Design choices:**

* **ContextVar parent stack** isolates concurrent `with` builders (sync + async).
* **Per-root tree lock** (`ux_dom.dom.src.concurrency`) serializes mutate+serialize on the same tree; independent roots do not share locks.
* **Pretty layout** lives in `Tags` (`ext.py`); compact stream reuses the same attribute helpers so walk ≡ render.
* **Cycle guard** emits `<!--cycle:Name-->` instead of stack overflow.

---

## 4. Component ontology

| Type | Base | Intent |
|------|------|--------|
| **`Component`** | dataclass-friendly | `render()` returns DOM; class attrs merge carefully |
| **`Fragment`** | Component, `render_tag=False` | Multi-root / invisible shell; unique attrs (e.g. `id`) once |
| **`ReactiveComponent`** | Component | Field mutation re-renders; **fail-closed** (rollback state + tree on render error) |
| **`XElement`** | Component | Class = definition registry; construct = host `<x-name>` |
| **`CustomElement`** | XElement | Light DOM clone (no shadow) |
| **`WebComponent`** | XElement | Shadow root required (`shadowroot` / `shadowdom`) |
| **`AlpineComponent`** | AlpineElement + XElement | Requires `x-tagname` + `x-data` |

**Registry SSoT:** `xelement_registry` — one definition per class / `x-tagname`. Document auto-collects hosts → one `<template x-tagname>` each.

**Attr contract:** only **`x-tagname`** (not `x-component`). Lint fails that form.

---

## 5. Tags / HTML serialize (`ext.Tags`)

| Public-ish surface | Role |
|--------------------|------|
| `Tags.clean_attribute` | Python kwargs → HTML/Alpine/HTMX names |
| `_render` / `_walk_render_tokens` | Pretty list vs compact stream |
| `CONTROL_ATTRS` | `self_dedent`, `child_dedent`, `open_tag`, `close_tag`, `render_tag` — not emitted as HTML |
| `StyleTags` | CSS rule dialect (underscore→dash; **no** Alpine `@` rewrite) |

**MRO:** `html_tag → Tags → dom_tag → dom1core`. Do not invent a second lock domain in `Tags`.

---

## 6. Document & plugins

```text
Document.use(XElement(), Htmx(), Csp.auto())
document.mount(app)   # served_files + middleware + optional StaticFiles hints
document(*page)       # two-stage head/body composition
```

| Plugin / runtime | Injects | Mounts |
|------------------|---------|--------|
| `XElement` / `XElementRuntime` | `<script src=/ux-dom/static/x_element.js>` | SafeStaticFile for that JS only |
| `Htmx` / `HtmxControl` | CDN or pinned HTMX (+ optional SSE ext) | middleware optional |
| `Csp` / `Csp.auto()` | policy middleware + nonce stamp | middleware |
| `Channel` | uxchannel tags if installed | optional package static |

**Design choice:** Document is SSoT; `App` / `CreateAsgi` are sugar, not a second document.

---

## 7. Routing & response

| Surface | Intent |
|---------|--------|
| `DirectoryRouter` | File path `routes/users/[id].py` → `/users/{id}` |
| `StreamingRoute` / `HTMLResponse` / `StreamingResponse` | Serialize tree; streaming uses compact tokens (`pretty=False`) by default |
| `ux_dom.response` | Public adapters over Starlette/FastAPI |

---

## 8. Optional peer packages

Live control plane is **optional** and lives in a **separate** package.
Do not mix its PyPI / import / CLI names into ux-dom brand lines.

## 8b. DX CLI intent (side effects)

| Command | Writes? | Gate |
|---------|---------|------|
| `templates` `examples` `ui` `plugins` `doctor` `lint` | No | — |
| `create-app` | Yes | confirm / `--yes`; **overwrite only `--force`** (`--yes` ≠ force) |
| `add` | Yes | refuse existing unless `--force` |
| `deploy` | Yes | skip existing unless `--force` |
| `build` | Tailwind if present; **no** dual JS copy by default; `dist/` only with `--package`/`--archive` | flags |
| `dev` | Only if `--tailwind` runs CSS build | does **not** copy `x_element.js` |

### Automation-first (ceremonial code)

Generators are the **default opt-in** path for app boilerplate. Hand-write
only when extending features or making breaking contract changes.

| Need | Automate | Hand-code |
|------|----------|-----------|
| Greenfield app | `uxdom create-app` | — |
| Stubs (component/route/xelement) | `uxdom add` | After generate, for real logic |
| UI kit copy-in | `uxdom add ui` | New primitives |
| Integrity | `uxdom doctor` | — |

See [CLI.md](../guides/CLI.md) · [DX.md](../guides/DX.md) ·
[MAINTENANCE_CANON.md](../ship/MAINTENANCE_CANON.md) §5.5.

---

## 9. Concurrency & safety

* **Per-root `RLock`** registry (weak-id map); multi-root locks ordered by `id` to avoid deadlock.
* **`replace_children`** atomic under lock.
* Reactive re-render is **fail-closed** (rollback fields + tree on render error).

Details: [CONCURRENCY.md](CONCURRENCY.md) · [MEMORY_TREE.md](MEMORY_TREE.md).

---

## 10. Where to read next

| Goal | Doc |
|------|-----|
| Day-1 mental model | [START_HERE.md](../START_HERE.md) |
| Layer ownership diagram | [ARCHITECTURE.md](ARCHITECTURE.md) |
| Every package path | [MODULE_MAP.md](MODULE_MAP.md) |
| Non-regression canon | [MAINTENANCE_CANON.md](../ship/MAINTENANCE_CANON.md) |
| Brittle edges | [STABILITY.md](../ship/STABILITY.md) |
