# Public & private API surface (0.1.0)

### Brand lines

| Layer | Name |
|-------|------|
| **PyPI / pip** | `ux-dom` |
| **Import** | `ux_dom` |
| **CLI** | **`uxdom`** |


---

## Top-level (`import ux_dom`)

| Symbol | Kind | Notes |
|--------|------|--------|
| `__version__` | str | e.g. `"0.1.0"` |
| `Document` | class | HTML shell SSoT (from settings) |
| `Component` | class | Base component |
| `Fragment` | class | Tagless multi-child |
| `ReactiveComponent` | class | Reactive fields + fail-closed re-render |
| `XElement` / `Htmx` / `Csp` / `Channel` | facades | From `ux_dom.runtime` |
| `WebAssets` / `TailwindCommand` | settings | Assets & CSS pipeline |
| `CreateProject` | helper | Optional scaffolding API |

---

## DOM (`from ux_dom.dom import …`)

| Surface | Notes |
|---------|--------|
| HTML tags (`div`, `span`, `form`, …) | Construct trees; support `with` / `async with` |
| `template`, `slot`, `script`, `style` | Standard elements |
| `defHTML` / parse helpers | Parse HTML string → nodes; `escape=True` sanitizes |
| Serialize | `node.__render__(pretty=…)`, `__async_render__`, `str(node)` |

### Custom elements (`ux_dom.dom.htmlelement`)

| Class | Public contract |
|-------|-----------------|
| `XElement` | subclass + `render` returns `template(..., **{"x-tagname": name})`; **construct = host** |
| `CustomElement` | Light DOM; **forbids** shadow attrs |
| `WebComponent` | **Requires** `shadowroot` or `shadowdom` |
| `AlpineComponent` | XElement + Alpine (`x-data` in definition tree) |
| `xelement_registry` | Process-wide definition SSoT; `.clear()` tests only |

---

## Runtime plugins (`ux_dom.runtime` / `ux_dom.plugins`)

| Facade | Behaviour |
|--------|-----------|
| `XElement()` | Head script → `/ux-dom/static/x_element.js` from package |
| `Htmx(...)` | HTMX script tags; optional SSE extension |
| `Csp.auto()` | Nonce CSP middleware + stamp |
| `Channel.optional(...)` | uxchannel if installed |

Document API:

```python
document = Document(...).use(XElement(), Htmx(), Csp.auto())
document.mount(app)   # static allowlist + middleware
html = str(document(page_content))
```

---

## Routing & response

| API | Module |
|-----|--------|
| `DirectoryRouter` | `ux_dom.routing.fastapi` |
| `StreamingRoute` | same |
| `HTMLResponse` / `StreamingResponse` | `ux_dom.response` |

---

## CLI (`uxdom` entry)

| Command | Side effects |
|---------|----------------|
| `create-app` | Writes scaffold; `--yes` ≠ overwrite; `--force` overwrites |
| `dev` | Runs server; no JS dual-copy; optional `--tailwind` CSS build |
| `doctor` / `lint` / `templates` / `examples` / `ui` / `plugins` | Read-only |
| `add` | Writes one stub; needs `--force` to overwrite |
| `build` | Checks + optional Tailwind; package only with `--package` |
| `deploy` | Writes provider files; `--force` to overwrite |

---

## Browser

| Asset | URL | Source |
|-------|-----|--------|
| `x_element.js` | `/ux-dom/static/x_element.js` | `ux_dom/scripts/x_element.js` in package |
| App CSS/images | `/assets/...` | Project `assets/` |

JS API: `window.UxDom.XElement.scan(root)`.

---

## Private / do not depend on

* `ux_dom.dom.src.concurrency._LOCKS*`
* Underscored methods not listed in guides (`_render_children` internals may move)
* `docs/archive/*` historical notes
* `demosite/` sample app

If you need a private helper in production code, open a discussion and promote it to a public export + this file.

## Concurrency (internal)

Not a day-1 application API. Trees are locked automatically; apps just call
``__render__`` / Document. Maintainers: ``scripts/profile_p95.py`` and
``docs/internals/CONCURRENCY.md``.

