# Public & private API surface (0.1.0)

> **Diátaxis:** reference · **Canonical:** `docs/reference/API_SURFACE.md` · **Layer:** ux-dom  
> Map: [INDEX.md](../INDEX.md).

### Brand lines

| Layer | Name |
|-------|------|
| **PyPI / pip** | `ux-dom` |
| **Import** | `ux_dom` |
| **CLI** | **`uxdom`** (pure-dom tooling only) |

Product lifecycle CLI: **`uxcompose`** (`create-app` · `build` · `serve` · `deploy` · `doctor`).

---

## Top-level (`import ux_dom`)

| Symbol | Kind | Notes |
|--------|------|--------|
| `__version__` | str | e.g. `"0.1.0"` |
| `Document` | class | HTML shell SSoT |
| `Component` / `Fragment` / `ReactiveComponent` | class | Trees |
| `XElement` / `Htmx` / `Csp` / `Channel` | facades | `ux_dom.runtime` |
| `WebAssets` | stub | Fail-closed — `from ux_compose import WebAssets` |
| `TailwindCommand` | stub | Fail-closed — use `uxcompose build` |

---

## DOM (`from ux_dom.dom import …`)

HTML tags, parse helpers, serialize via `node.__render__` / `__async_render__`.

---

## Document shell

```python
document = Document(...).use(XElement(), Htmx(), Csp.auto())
html = str(document(page_content))  # or tree.__render__()
```

Product HTTP delivery / host strategy: **ux-compose**, not Document.use.

---

## Discovery

Product page routing is **ux-compose** (`ux_compose.routing.DirectoryRoutes`).
Constructing `DirectoryRoutes` from this package fails closed.

---

## CLI (`uxdom` — pure-dom only)

| Command | Role |
|---------|------|
| `doctor` / `info` | Package / Document health |
| `lint` | Conventions |
| `profile` / `dashboard` | Render p95 |
| `add` | component \| xelement \| ui |
| `ui` | List UI kit |

**Product CSS is `uxcompose build`.** Product verbs create-app · build · serve · deploy live on **uxcompose**.

---

## Private / do not depend on

* Underscored render internals
* `docs/archive/*`
* Historical host / routing leftovers on this package (fail-closed; use ux-compose)
