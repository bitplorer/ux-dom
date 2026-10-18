# Public & private API surface (0.2.0)

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
| `__version__` | str | e.g. `"0.2.0"` |
| `Document` | class | HTML shell SSoT |
| `Component` / `Fragment` / `ReactiveComponent` | class | Trees |
| `XElement` / `Htmx` / `Csp` / `Channel` | facades | aliases of `ux_dom.plugins` (`XElementRuntime`, `HtmxControl`, `Csp`, `UxChannelRuntime`); `ux_dom.runtime` removed |

`WebAssets` and `TailwindCommand` are not on this package. App folders are `from ux_compose import WebAssets`. CSS minify is `uxcompose build`.

---

## DOM (`from ux_dom.dom import …`)

HTML tags, parse helpers, serialize via `node.__render__` / `__async_render__`.

### Stable seam for sibling packages

| Symbol | Kind | Defined in (private) |
|--------|------|----------------------|
| `Component` | class | `ux_dom.dom.src.component` |
| `dom_tag` | class | `ux_dom.dom.src.dom_tag` |
| `escape` | fn | `ux_dom.dom.src.utils.dom_util` |
| `raw` | fn | `ux_dom.dom.src.utils.dom_util` |

Import these from `ux_dom.dom`, not from `ux_dom.dom.src.*`. The `src` layout
is internal and may move; these four names are the supported path.

- **Why:** the siblings reach these four through private paths today:
  ux-compose (`Component`, `dom_tag`, `raw`), ux-channel (`escape`), and
  ux-motion (`Component`). They cover every private `ux_dom.dom.src.*` import
  in the siblings.
- **Status:** the names were already importable from `ux_dom.dom` through the
  star imports. They are now listed here, re-exported explicitly, and pinned by
  `tests/01_core/test_public_dom_seam.py`.
- `ux_dom.dom` has no `__all__` on purpose. A literal list would freeze every
  star-exported name (311 of them, including undecided ones) as public API.

## Serialize (`from ux_dom.response.serialize import …`)

| Symbol | Kind | Notes |
|--------|------|--------|
| `to_html_bytes` | fn | Tree / Component / str → UTF-8 HTML bytes |
| `extract_by_id` | fn | Outer-HTML slice for `#id` (C2). `Fragment` builds trees; this extracts. Compose `_fragment_for_target` KEEP until callers USE this. Channel `_guess_target_from_html` is selector leftover — not extract. Not on root `__all__`. |

HTTP adapters (`HTMLResponse`, …) stay optional. Product delivery is ux-compose.

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
This package ships no file router: `ux_dom.routing` was removed (F-18).

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
* Deleted product shells (`WebAssets`, `TailwindCommand`, `CreateProject`, host / HMR plugins) are absent — not fail-closed classes
* `ux_dom.routing`, `DirectoryRouting`, `App.routes()`, `uxdom add route` — removed (F-18)
