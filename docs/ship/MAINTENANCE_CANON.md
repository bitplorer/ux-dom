# ux-dom maintenance canon (0.1.0+)

**Audience:** maintainers and long-term design decisions.  
**Status:** canonical — prefer this over scattered audit notes when they conflict.  
**Related:** [ARCHITECTURE.md](../internals/ARCHITECTURE.md) · [RENDER_PHASES.md](../internals/RENDER_PHASES.md) · [DOCUMENT_TWO_STAGE.md](../guides/DOCUMENT_TWO_STAGE.md) · [MEMBERSHIP.md](../internals/MEMBERSHIP.md) · [MEMORY_TREE.md](../internals/MEMORY_TREE.md) · [BUGS_AUDIT.md](BUGS_AUDIT.md)

This document answers four questions:

1. **What is the library for?** (intent that must not be diluted)
2. **What structure must stay?** (layers and contracts)
3. **What was broken and fixed?** (so we do not reintroduce bugs)
4. **What may change, and when?** (safe touch map)

---

## 1. Intent (do not dilute)

ux-dom is **not** a thin HTML string helper. It is a **Python-first hypermedia UI stack**:

| Pillar | Meaning |
|--------|---------|
| **DOM as values** | Tags / Components are trees you can `add`, `get`, `in`, serialize sync/async |
| **Hypermedia first** | HTMX, Alpine, Web Components / XElement — not a React clone in Python |
| **Channel optional** | `uxchannel` (or similar) multiplexes events; UI never hard-depends on one transport |
| **Document is the shell** | Clear **head / body** and two-stage placement — not a guessy “App hub” |
| **FastAPI is the spine** | Routes, middleware, mounts stay explicit; Create* helpers are optional |
| **DX for decades** | `create-app`, Tailwind/HMR, doctor/build, plugins replaceable without rewriting apps |

**Preserve usage pattern:** `with div(): …`, `Component.render → tree`, `Document(*page)`, file routes like Next (`[id]` folders), `document.use(runtime)`.

**Do not “simplify” by removing:** DirectoryRouter, XElement registry, dual attribute cleaning (dialect vs HTML), two-stage Document, sync **and** async serialize, context-manager build (`with` / `async with`).

---

## 2. Structure that must be maintained

### 2.1 Layer cake (stable boundaries)

```text
┌─────────────────────────────────────────────────────────────┐
│  App code / examples / create-app scaffold                  │
├─────────────────────────────────────────────────────────────┤
│  CreateProject · CLI (create-app, doctor) · CreateAsgi sugar │  ← DX
├─────────────────────────────────────────────────────────────┤
│  Document · HtmlDocument · runtimes (.use) · CSP middleware │  ← shell + policy
├─────────────────────────────────────────────────────────────┤
│  DirectoryRouter · HTMLRoute / StreamingRoute · response    │  ← HTTP surface
├─────────────────────────────────────────────────────────────┤
│  Component · XElement · Tags · dom_tag · membership/get     │  ← tree model
├─────────────────────────────────────────────────────────────┤
│  plugins / assets / SafeStatic · WebAssets / package_mount  │  ← shipping JS
├─────────────────────────────────────────────────────────────┤
│  FastAPI / Starlette (external) · optional uxchannel │  ← host / bridge
└─────────────────────────────────────────────────────────────┘
```

**Rules:**

- **Tree layer** must not import FastAPI.
- **Document** owns head/body placement; **runtimes** attach via `.use()` with validation (unique names, head/body/mount/served_files).
- **CSP** is **middleware + stamp**, not a channel concern and not a second ad-hoc injector.
- **Static JS** ships via **package_mount / SafeStatic allowlist** (no double-copy into app static by default; no open filesystem).
- **Scaffold** wires FastAPI + `document.mount` + DirectoryRouting; CreateAsgi is optional sugar only.

### 2.2 Package map (mental model)

| Path | Owns |
|------|------|
| `ux_dom/dom/src/dom_tag.py` | Base node, context stack, `get` / `_find` / `matches` / `in`, `__render__` / `__async_render__` |
| `ux_dom/dom/src/ext.py` | Tags layout, `clean_attribute`, sticky control flags, **token walk / pretty stream** |
| `ux_dom/dom/src/component.py` | Build-time `render()`, Component transparency `_entry`, Reactive re-render |
| `ux_dom/dom/htmlelement.py` | XElement / CustomElement / host-first `__new__`, registry |
| `ux_dom/dom/htmldocument.py` | HtmlDocument shell, `__pre_render__` (defs, charset, …) |
| `ux_dom/document.py` | Document factory, **two-stage** call, `.use()` runtimes |
| `ux_dom/routing/` | DirectoryRouter, path cleaning, `[id]` → `{id}` |
| `ux_dom/runtime/` | XElement, Htmx, Channel, Csp adapters |
| `ux_dom/create/` | CreateAsgi, CreateProject (scaffolds) |
| `ux_dom/plugins/`, `ux_dom/assets/` | Pluggable contribution / SafeStatic |
| `ux_dom/ui/` | Optional shadcn-style kit (variants, `cn`) — optional moat, not core |
| `ux_dom/scripts/` | `x_element.js` / html_elements runtime (name-aligned with XElement) |

### 2.3 Three “apps” the user must always locate

```text
DOM     →  Document(*content) / Component trees
API     →  FastAPI routes (DirectoryRouter or explicit)
Middleware →  document.mount(app) / app.add_middleware(...)
```

No guesswork. If a feature blurs these, redesign the feature — do not invent a mega-`App.use()` that hides placement.

---

## 2.4 Sync/async context (ContextVar)

Build stack and request vars use **`contextvars.ContextVar`** (one mechanism for
sync threads and asyncio Tasks). Pair:

* `with` → `__render__`
* `async with` → `__async_render__`

Details: [CONTEXT_SYNC_ASYNC.md](../internals/CONTEXT_SYNC_ASYNC.md).

## 3. Contracts that must not break (without a major version)

### 3.1 Two-phase “render” (naming trap)

| Name | Phase | When | Frequency |
|------|-------|------|-----------|
| `Component.render(*args)` | **Build** | constructor | Once per instance (except Reactive) |
| `__render__` / `_render` / `_walk_render_tokens` | **Serialize** | `str`, StreamingResponse | Once per output |
| `HtmlDocument.__pre_render__` | **Pre-serialize** | start of serialize | Once per output |

- `str(node)` **must not** re-call `Component.render`.
- XElement **definition** `render` runs **once per class** (registry SSoT); hosts are templates.
- Tests: `tests/test_render_phases.py`.

### 3.2 Document two-stage placement

| Stage | API | HTML position |
|-------|-----|----------------|
| **A init** | `Document(head=…, body=…)` + `.use()` | `common_head` / `common_body` (after call-head; end of body) |
| **B call** | `doc(*content, head=…, body=…)` | early head / early body |

Order is **deliberate** (HTMX after content, runtimes in common, page title in call-head).  
Callables in stage lists are **hooks** (e.g. nonce-aware tags) — filter with `_is_stage_hook` so **dom_tag instances are not treated as callables**.

### 3.3 Membership triad

| API | Faces (self + Component `_entry`) | Descendants |
|-----|-----------------------------------|-------------|
| `matches` | yes | **no** |
| `get` / `_find` | yes | yes |
| `x in node` | yes | yes (lazy) |
| `bool(node)` | always **True** (node exists) | — |
| `len(node)` | children (Component: of `_entry`) | — |

- Dual **clean_attribute** (dialect vs emission) is a **design feature**, not a bug.
- `in` / existence use **`_find` short-circuit** — never `len(get())` full lists.
- Tests: `tests/test_membership_*`, `tests/test_find_lazy_membership.py`.

### 3.4 DirectoryRouter path rules

| On disk | URL intent |
|---------|------------|
| `app/users/[id]/` | `/users/{id}/` — **`[id]` is intentional** (Python cannot use `{id}` as folder name) |
| `app/shop/route.py` | `/shop/…` |
| Private `_foo` | cleaned from URL segment; treat import policy carefully |

Do **not** “fix” `[id]` by stripping brackets without converting to FastAPI `{id}`.

### 3.5 Serialize / memory

| Mode | Behavior |
|------|----------|
| Tree `children` | **List-backed** (mutable DOM) — by design |
| `pretty=False` stream | Pure generator open→children→close, **O(1)** tokens |
| `pretty=True` stream | Exact layout engine; **bounded queue** (default 256), one pass, **no tee** |
| `str(node)` | Full string (by definition) |

Production StreamingResponse: **`pretty=False`**.

### 3.6 Sticky control flags

`render_tag`, `self_dedent`, `child_dedent`, `open_tag`, `close_tag` must use **sticky `_control`** (read, do not permanent `pop`).  
Otherwise second `str()` / parent re-render corrupts layout. Control keys **never** emit as HTML attributes (`CONTROL_ATTRS`).

### 3.7 Attribute dialects

- `hx_on_click` → `hx-on:click` (**not** `h@click` — never apply `x-on-` → `@` as a **substring** of `hx-on-`).
- `ws_send` / `sse_connect` → `ws-send` / `sse-connect`.
- `class_` / `for_` → `class` / `for` (trailing `_` keyword workaround).
- Leading `_` strip for reserved words remains.

### 3.8 Assets & security

- Plugin / package JS: **single copy** from installed package; alias via SafeStatic **allowlist** (URL regex, extension, package containment).
- Script **dedupe** by identity/src when injecting runtimes.
- CSP: **one owner** — middleware generates nonce; Document stamp applies to script/style; streaming must not reset contextvar early.

### 3.9 XElement / JS name alignment

Python `XElement` / `x-tagname` ↔ browser runtime (`x_element.js` / html_elements) — **one conceptual name**.  
Definition auto-collection in `__pre_render__` for **both** sync and async serialize.

---

## 4. Serious issues found and resolved

Grouped by theme. IDs cross-ref [BUGS_AUDIT.md](BUGS_AUDIT.md) where applicable.

### 4.1 DirectoryRouter (ship-blockers)

| Issue | Fix / rule |
|-------|------------|
| `str.replace(base)` corrupted paths (`application` → `lication`) | Path-prefix cleaning only |
| `[id]` folders “broken” | Feature: map to `{id}` — not a bug |
| classmethod route name setattr crash | Unwrap `__func__` / safe rename |
| Pseudo `_FILE_ROUTES` paths | Separate file-function registration |
| Root from `__main__.__file__` only | `package_dir=` explicit |
| Duplicate routes silent | Detect / warn |
| FastAPI `strict_content_type` TypeError | Filter kwargs to APIRoute signature |

### 4.2 Render / serialize

| Issue | Fix / rule |
|-------|------------|
| Fear of “double render” on init | Two phases: build `render` vs serialize — document + tests |
| Async stream missing XElement defs | `__pre_render__` on compact walk too |
| Pretty stream double `__pre_render__` | Walk pre only when not going through HtmlDocument `_render`; one per serialize |
| Pretty = full list then yield | Bounded-queue stream for exact layout; compact pure generator |
| `in` / get nested full lists | `_find` generator; `__contains__` short-circuit |
| Cycle parent↔child infinite serialize | `_seen` set → `<!--cycle:Name-->` |
| Control flags popped → second serialize wrong | Sticky `_control` + skip `CONTROL_ATTRS` in HTML |

### 4.3 Attribute / dialect

| Issue | Fix / rule |
|-------|------------|
| `hx_on_click` → `h@click` | Prefix-only Alpine `@` rewrite; then `hx-on-*` → `hx-on:*` |
| `ws_` / `sse_` not dashed | Special prefixes |
| `class_` not cleaned | Trailing `_` identifier strip |

### 4.4 Document / App / CSP / assets

| Issue | Fix / rule |
|-------|------------|
| Long `App.use()` chain hid head/body | Runtimes on **Document.use**; FastAPI stays spine |
| CSP “owned by channel” confusion | **Csp** middleware only; stamp at document |
| StreamingResponse nonce lost | ASGI send_wrapper + finally; do not reset context early |
| Double script injection | Dedupe on inject |
| “Copy JS into app static” dual copy | package_mount + SafeStatic; no mandatory second copy |
| Open static filesystem risk | Allowlist only |

### 4.5 Component / XElement

| Issue | Fix / rule |
|-------|------------|
| Host-first construction double-init | `__xelement_definition__` / registry; public `Hello()` → host only |
| Definition render N times for N hosts | Once per class |
| `matches` vs `get` vs `in` unclear | Formal faces scope (MEMBERSHIP.md) |
| `__bool__` always True | Intent: instance existence, not “has children” — use `len` |

### 4.6 DX / shipping

| Issue | Fix / rule |
|-------|------------|
| Tailwind HMR / detect hang | Non-blocking detect; watch optional |
| Scaffold vs runtime name drift | Align create-app with Document + CreateAsgi + x_element.js |
| Build without inventing second asset tree | Doctor/build check package serve paths |

---

## 5. What to touch — and when

### 5.1 Never touch casually (requires major version + migration guide)

| Area | Why |
|------|-----|
| `Component.render` as **build** API | Entire ecosystem of subclasses |
| Document two-stage order | Head/body scripts break if reordered blindly |
| `matches` / `get` / `in` triad | Semantic surface used in app logic |
| DirectoryRouter `[id]` → `{id}` | File-based routing contract |
| Host-first XElement + registry SSoT | Upgrade model for custom elements |
| List-backed `children` | Mutable tree, parents, partials |
| Dual clean_attribute dialects | HTMX/Alpine/Vue coexistence |
| FastAPI as real spine (not hidden) | Production debuggability |

### 5.2 Touch carefully (needs tests in the same PR)

| Area | Required tests |
|------|----------------|
| `ext.py` layout / pretty stream | Golden HTML + `test_pretty_stream` + idempotent re-render |
| `dom_tag` membership / `_find` | Membership contract + lazy tests |
| HtmlDocument `__pre_render__` | Sync + async + XElement defs |
| DirectoryRouter cleaning | Path chaos cases (`application`, `[id]`, duplicates) |
| CSP nonce + StreamingResponse | Concurrent requests, stream finish |
| SafeStatic allowlist | Path traversal / extension / package escape |
| Runtime `.use` placement | Head vs body fixtures |
| Sticky control flags | Second `str()` equals first |

### 5.3 Safe to evolve (prefer plugins / Create*)

| Area | How |
|------|-----|
| New runtimes (Alpine CDN, analytics) | Implement runtime protocol → `document.use(...)` |
| UI kit / shadcn-style | `ux_dom.ui` optional |
| Scaffold templates | CreateProject only |
| Doctor checks / build packaging | CLI layer |
| Tailwind integration | Optional tool path; never block import |
| Channel backend swap | Hypermedia bridge interface; Document tags only |

### 5.4 Prefer not to “fix” (often intentional)

| Appearance | Reality |
|------------|---------|
| `[id]` in URLs from folders | Feature (Python filesystem) |
| Dual clean_attribute | Feature (dialect consistency) |
| `bool(node)` always True | Feature (existence) |
| Component `render` vs `__render__` names | Historical; document, don’t rename lightly |
| Pretty stream uses helper thread + queue | Engineering trade for exact layout |
| Private `_` route modules | Policy choice — document import rules |

---

## 6. How to change safely (checklist)

Before any core change:

1. **Name the contract** (which table in §3).
2. **Add/adjust a test that would have failed** on the old bug (not only a happy path).
3. Run: membership, render_phases, pretty_stream, DirectoryRouter chaos, CSP/stream, create-app smoke, full suite.
4. Confirm **`npm`/JS** only if runtime scripts changed; keep Python↔JS names aligned.
5. Update **this file** + the specific deep doc (MEMBERSHIP, RENDER_PHASES, …).
6. Prefer **plugin/runtime** over core if the change is optional capability.

### Production defaults

```text
StreamingResponse  →  pretty=False
Document           →  explicit ensure_csrf_token policy per app
Static             →  package_mount / SafeStatic, not open StaticFiles of site-packages root
CSP                →  document.use(Csp()); stamp scripts
Routes             →  DirectoryRouter(package_dir=...) or explicit FastAPI
```

---

## 7. Recommended app skeleton (canonical)

```python
from fastapi import FastAPI
from ux_dom import Document
from ux_dom.create import CreateAsgi
from ux_dom.runtime import XElement, Htmx, Csp
from ux_dom.dom import meta, title

document = Document(
    head=[meta(charset="utf-8"), meta(name="viewport", content="width=device-width")],
    body=[],
    ensure_csrf_token=False,  # or True if your stack needs it
).use(
    XElement(),
    Htmx(middleware=True),
    Csp(),  # middleware + nonce stamp only here
)

app = (
    CreateAsgi(title="App", document=document, debug=True)
    .directory_routes(PACKAGE, "routes")
    .static("/assets", ASSETS)
    .build()
)

# page
@app.get("/")
def home():
    return document(
        # content...
        head=[title("Home")],
    )
```

Or pure FastAPI: `document.mount(app)` + explicit routes — same contracts.

---

## 8. Test map (regression anchors)

| Concern | Tests (indicative) |
|---------|-------------------|
| Build vs serialize | `test_render_phases.py` |
| Pretty/compact stream | `test_pretty_stream.py` |
| Lazy membership | `test_find_lazy_membership.py`, membership_* |
| Document stages | `test_document_two_stage.py` |
| XElement defs async | `test_auto_xelement_definitions.py` |
| Router cleaning | DirectoryRouter / v05 / chaos suites |
| CSP / static | `test_csp_nonce.py`, `test_safe_static.py` |
| Idempotent control | `test_production_hardening.py` |
| Scaffold | `test_dx_cli.py`, package_static |

**Bar:** full `pytest` green before release; production build of create-app scaffold when DX changes.

---

## 9. Historical anti-patterns (do not reintroduce)

1. **Mega-App hub** that invents head/body placement by plugin order alone.
2. **`len(node.get(x)) > 0` for membership** (full lists).
3. **`attributes.pop` of control flags** during serialize.
4. **Substring `x-on-` → `@`** that mutilates `hx-on-`.
5. **`base_directory` string replace** for path cleaning.
6. **Pre-render only on sync `_render`** (async stream missing defs).
7. **Copy every package JS into app/static** as the only ship path.
8. **CSP owned by channel runtime**.
9. **Treating `[id]` routes as bugs**.
10. **Renaming Component.render** without a decade-long migration plan.

---

## 10. Open / residual risks (honest)

Track in BUGS_AUDIT / STABILITY; do not pretend zero:

- DirectoryRouter private-module import policy tightening.
- True async *child* await inside tree build (async serialize is stream of built tree).
- Tailwind generated config drift (jit mode / plugins) as tooling evolves.
- Multi-worker unique IDs if used for security (not just cache bust).
- Residual golden-file sensitivity of pretty layout edge cases.

When in doubt: **preserve capability and usage pattern**; un-bloat only behind stable facades.

---

## 11. One-page decision tree

```text
New capability?
  → Optional runtime/plugin?  document.use(X) + SafeStatic if JS
  → Scaffold only?            CreateProject
  → Tree semantics?           Extend dom_tag/Component with membership tests
  → HTTP?                     FastAPI route or DirectoryRouter — explicit

Bug report “double render”?
  → Build or serialize?       See §3.1 — almost never double build

Bug report “async memory”?
  → Tree size vs token buffer?  children are lists; use pretty=False + _find

Bug report “route wrong”?
  → [id] feature? path-prefix?  See §3.4

Breaking change needed?
  → Major version + migration + this doc §5.1 list
```

---

*Last consolidated for ux-dom 0.1.0 production line. Update this file whenever a §3 contract or §4 fix class changes.*
