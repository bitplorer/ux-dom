> **Start:** [START_HERE.md](../START_HERE.md) · **Architecture:** [ARCHITECTURE.md](../internals/ARCHITECTURE.md)

# Document API — complete guide

ux-dom’s `Document` is the **single source of truth for the HTML shell**. FastAPI is the **process**. Do not use `App` or `CreateAsgi` as a second document.  
Runtimes attach to a Document instance; they affect either the **DOM** (tags) or
the **ASGI app** (`mount`), never by guesswork.

---

## 1. Mental model

```text
Document(head=…, body=…)     Stage A chrome  →  common_head / common_body
  .use(XElement(), Htmx())   Stage A runtimes →  tags into common_* by placement
  .mount(app)                ASGI only        →  static routes + middleware
  (*content, head=…, body=…) Stage B          →  page head first, content, then common body
```

| Concern | Owner |
|---------|--------|
| `<head>` / `<body>` order | `Document` + `HtmlDocument.render` |
| HTTP routes, middleware | FastAPI (`document.mount(app)` wires runtimes) |
| Scaffold | `uxdom create-app` → FastAPI + `document.mount` + DirectoryRouting |

---

## 2. Two-stage placement (DOM)

### Stage A — construction

```python
document = Document(
    head=[meta(charset="utf-8")],   # common_head
    body=[],                        # common_body
)
```

### Stage B — call

```python
document(
    page_component,                 # body children
    head=[title("Home")],           # call head — FIRST in <head>
    body=[],                        # call body — early in <body>
)
```

### Order inside HTML (fixed)

```text
<head>
  [B] call-time head
  [A] common_head  (+ runtime document_head tags)
</head>
<body>
  *content
  [B] call-time body
  placeholders (Body / XElement defs)
  [A] common_body  (+ runtime document_body tags)
</body>
```

**Do not flatten** call and common lists into one bag — order is intentional.

### Callables in lists (stage hooks)

Only **functions/lambdas** are hooks. Tags (`div`, `meta`, …) are also callable
for context-manager sugar and are **never** invoked as hooks.

```python
Document(
    head=[
        meta(charset="utf-8"),
        lambda ctx: meta(name="x-nonce", content=ctx["nonce"])
        if ctx.get("nonce")
        else None,
    ]
)
```

`ctx` keys: `document`, `nonce` (CSP middleware), `webassets`, plus call kwargs.

---

## 3. `document.use` — shared runtimes

**Instance method** (not a classmethod). Mutates this Document.

```python
document = Document(head=[...], body=[]).use(
    XElement(),              # → common_head + SafeStaticFile route
    Htmx(middleware=True),   # → common_body + HtmxMiddleware
    Csp(),                   # → middleware only (no tags)
)
```

### Rules

| Rule | Behavior |
|------|----------|
| Validation | Runtime must expose at least one of: `document_head`, `document_body`, `mount`, `served_files`, `artifacts`, `wire` |
| Names | Same `name` → **replace** previous runtime on this instance |
| `None` | Skipped |
| Placement | Tags go to **common_** head/body only (stage A) |

### Default runtime placement

| Runtime | DOM | ASGI (`mount`) |
|---------|-----|----------------|
| `XElement` | `<script>` in common_head | `GET /ux-dom/static/x_element.js` |
| `Htmx` | CDN scripts in common_body | optional HtmxMiddleware |
| `Channel` | script tags in common_head | usually channel `attach`, not ux_dom |
| `Csp` | (none) | CSP nonce middleware |

---

## 4. `document.using` — page-local fork

Does **not** mutate the shared shell.

```python
# shared
document = Document(...).use(XElement(), Htmx())

# most pages
return document(Home(), head=[title("Home")])

# one page needs more
return document.using(Channel.optional())(
    Live(),
    head=[title("Live")],
)
```

### Implementation sketch

```text
using(*runtimes)
  → copy()           # new Document, list(_runtimes), list(head/body)
  → child.use(*runtimes)
  → return child
```

### Equivalent call-time form

```python
document(Live(), head=[title("Live")], use=[Channel.optional()])
# internally: target = self.using(*use) for this response only
```

### Cases

| Case | Pattern |
|------|---------|
| App-wide XElement + HTMX | `document.use(XElement(), Htmx())` once |
| One admin page needs CSP meta debug | callable in `head=` or `using` not required |
| One live page needs channel scripts | `document.using(Channel.optional())(…)` |
| Replace HTMX version on one page | `using(Htmx(version="2.0.4"))` (same name replaces on **child** only) |
| Parent must stay clean | always prefer `using` / `use=` over `use` on the shared instance |

### Limits

- Runtime **objects** on parent and child may be the **same instance** after copy (list is new; objects are shared). Do not store per-request state on the runtime object.
- **`mount(app)`** only sees the instance you mount (usually the shared `document`). Page-only runtimes that need **new static URLs** must also be on the shared shell’s `.use` (or you mount a union at startup).

---

## 5. `document.mount` — ASGI bridge

Not DOM. Applies attached runtimes to a FastAPI/Starlette app **once at startup**.

```python
app = FastAPI(title="MyApp")
document.mount(app)
```

### What it does (in order)

1. For each runtime: collect `served_files()` → install allowlisted routes (`SafeStaticFile`)
2. For each runtime: call `runtime.mount(app)` if present (CSP, HTMX middleware, …)
3. For each runtime: `package_static_mounts()` directory mounts if any (rare)

### What it does **not** do

- Does not set head/body order  
- Does not run per request  
- Does not mount page-only `using()` forks unless you mount that fork too  

### Cases

| Case | Code |
|------|------|
| Pure FastAPI | `app = FastAPI(); document.mount(app)` |
| Via FastAPI | `app = FastAPI(...); document.mount(app)` |
| XElement only | `.use(XElement())` then `mount` → script tag works at `/ux-dom/static/x_element.js` |
| CSP | `.use(Csp())` then `mount` → nonce middleware; tags stamped at render when nonce set |
| No Document mount | You must wire static + middleware yourself; tags alone will 404 |

### Security note

`served_files` is allowlist-based (URL pattern, extension, package containment).  
Prefer that over wide `StaticFiles` directory mounts for library JS.

---

## 6. Full application cases

### Case A — Minimal hypermedia app

```python
# document.py
from ux_dom import Document
from ux_dom.dom import meta, title
from ux_dom.runtime import Htmx, XElement

document = Document(
    head=[meta(charset="utf-8")],
    body=[],
).use(XElement(), Htmx(middleware=True))

def page(*content, page_title="App"):
    return document(*content, head=[title(page_title)])

# main.py
from fastapi import FastAPI
from app.document import document

app = FastAPI(title="App")
document.mount(app)

@app.get("/")
def home():
    from ux_dom.response.starlette import HTMLResponse
    return HTMLResponse(page(Home()))
```

### Case B — Explicit FastAPI assembly (preferred)

```python
from fastapi import FastAPI
from app.document import document

app = (
    # preferred:
    # app = FastAPI(title="Shop", debug=True)
    # document.mount(app)
    .directory_routes(PACKAGE, "routes")
    .static("/assets", ASSETS_DIR)
    .build()
)
```

### Case C — Page-local channel scripts

```python
# shared document.use has XElement + Htmx only
# live route:
return document.using(Channel.optional(mount_via_ux_dom=False))(
    LiveView(),
    head=[title("Live")],
)
# Channel bytes: Channel.boot / attach_channel(app) separately
```

### Case D — CSP with nonce-aware meta

```python
document = Document(
    head=[
        meta(charset="utf-8"),
        lambda ctx: meta(name="x-csp-nonce", content=ctx["nonce"])
        if ctx.get("nonce")
        else None,
    ],
    body=[],
).use(XElement(), Htmx(), Csp(strict_dynamic=True))

app = FastAPI()
document.mount(app)  # CSP middleware
```

### Case E — Call-time assets only (no extra runtime)

```python
return document(
    Report(),
    head=[
        title("Report"),
        link(href="/assets/report.css", rel="stylesheet"),  # stage B head
    ],
    body=[script(src="/assets/report.js")],  # stage B body, before common_body
)
```

---

## 7. API cheat sheet

| API | Mutates? | Affects DOM? | Affects ASGI? |
|-----|----------|--------------|---------------|
| `Document(head, body)` | n/a | common_* | no |
| `document.use(*rt)` | yes | common_* tags | via later `mount` |
| `document.using(*rt)` | no (copy) | copy’s common_* | only if you `mount` the copy |
| `document(*c, head=, body=, use=)` | no | yes | no |
| `document.mount(app)` | app | no | yes |
| `document.copy()` | no | n/a | n/a |
| `document.runtimes()` | no | inspect | inspect |

---

## 8. Related docs

- [DOCUMENT_TWO_STAGE.md](DOCUMENT_TWO_STAGE.md) — order details  
- [ARCHITECTURE.md](../internals/ARCHITECTURE.md) — App vs Document vs Create*  
- [CSP.md](../security/CSP.md) — nonce middleware  
- [SAFE_STATIC.md](../security/SAFE_STATIC.md) — allowlisted JS routes  


## Custom elements (hosts only)

See [XELEMENT_AUTO_DEFINITIONS.md](XELEMENT_AUTO_DEFINITIONS.md).

```python
class Hello(CustomElement):
    tag_name = "hello"
    def render(self, tag_name="hello"):
        return template(div("Hi"), **{"x-tagname": tag_name})

document(div(Hello(), Hello()))  # definitions auto-collected
```


---

## API quick reference

```python
Document(
    head=[...],           # stage A / init common_head seeds
    body=[...],
    ensure_csrf_token=False,
    webassets=None,
)

document.use(*runtimes) -> Document     # chainable; validates plugin surface
document.using(*runtimes) -> Document   # alias of use
document.runtimes() -> list             # attached runtimes
document.mount(app) -> app              # static routes + middleware
document(*content, head=..., body=..., page_title=...)  # render page
```

### Runtime order (recommended)

1. **XElement** — JS in head  
2. **Htmx** — scripts in body  
3. **Channel.optional()** — if installed  
4. **Csp.auto()** — middleware only; last among shell plugins is fine  

### page() helper (scaffold)

```python
def page(*content, page_title=None, **kw):
    return document(*content, head=[title(page_title)] if page_title else [], **kw)
```
