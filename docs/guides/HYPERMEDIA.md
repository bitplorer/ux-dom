# Alpine · Jinja · HTMX · Slots · Web Components

Honest map of what ux-dom provides, how to use it, and how thoroughly it is tested.

## Coverage status (0.1.0)

| Area | Library API | Examples | Unit tests | Headless browser |
|------|-------------|----------|------------|------------------|
| **XElement / CustomElement / WebComponent** | ✓ | ✓ xelement_kit light/shadow | ✓ strong | ✓ Playwright |
| **AlpineComponent** | ✓ | ✓ `/alpine/AlpineDemo` | ✓ attr matrix + browser toggle | ✓ |
| **HTMX attrs + middleware + partials** | ✓ | ✓ shop, showcase, kit | ✓ strong | partial (afterSwap in harness) |
| **HTML `<slot>` + shadow projection** | ✓ tags + WebComponent demos | ✓ shadow gallery | ✓ browser slotAssigned | ✓ |
| **`Slots` / `WebComponentSlot` helpers** | ✓ `ux_dom.slots` | ✓ kit `/slots/SlotsDemo` | ✓ render smoke | limited |
| **Jinja tags (`For`/`If`/`Block`/…) ** | ✓ `ux_dom.dom.src.jinjatags` | ✓ kit `/jinja/JinjaDemo` | ✓ `TestJinja` + kit | n/a (server HTML) |
| **`JinjaElement` class** | thin wrapper | documented | smoke | n/a |

## Alpine.js

**Python:** `AlpineElement` (requires `x-data`), `AlpineComponent` (`x-data` + `x-tagname`).

**Browser:** load Alpine CDN **and** `x_element.js`. Runtime calls `Alpine.initTree` after upgrade.

```python
from ux_dom.dom import div, template
from ux_dom.dom.htmlelement import AlpineComponent

class Toggle(AlpineComponent):
    def render(self, tag_name: str = "toggle"):
        return template(
            div(
                **{"x-data": "{ on: false }", "@click": "on = !on"},
            ),
            **{"x-tagname": tag_name},
        )
```

**See:** `docs/guides/XELEMENT.md`, `examples/xelement_kit/app/routes/alpine.py`,  
`tests/02_document_plugins/test_xelement_runtime.py`, `tests/06_browser/test_xelement_browser.py`.

## HTMX

**Python attrs:** `hx_get`, `hx_post`, `hx_target`, `hx_swap`, `hx_trigger`, `hx_on_*` → cleaned to HTMX dialect.

**Middleware:** `HtmxMiddleware` / plugin `HtmxControl` → `request.state.htmx`.

**With XElement:** after swap, `x_element.js` listens for `htmx:afterSwap` and scans new `x-tagname` definitions.

```python
button("Load", hx_get="/partial", hx_target="#panel", hx_swap="innerHTML")
```

**See:** showcase cart, hypermedia shop, `examples/xelement_kit/.../htmx.py`,  
`ux_dom/htmx/middleware.py`, HTMX tests under `tests/`.

## Jinja

Two layers:

1. **Jinja tag DSL** — `from ux_dom.dom.src.jinjatags import For, If, Block, Var, …`  
   Build trees that render to Jinja source; call `node(**context)` / `render_jinja` to expand.
2. **`JinjaElement`** — Component that delegates to `render_jinja` when called with options.

```python
from ux_dom.dom import li
from ux_dom.dom.src.jinjatags import For, Var

tpl = For("name in names", li(Var("name")))
html = tpl(names=["a", "b"])  # expanded HTML string/tree
```

**See:** `tests/01_core/test_ux_dom.py::TestJinja`, kit `/jinja/JinjaDemo`.

## Slots

| Mechanism | Use |
|-----------|-----|
| HTML `<slot>` / `slot(name=…)` in a **WebComponent** template | Standard projection |
| `ux_dom.slots.Slots` | Declarative multi-named slots + optional CSS list |
| `ux_dom.slots.WebComponentSlot` / `x_slot` | Alpine-assisted dynamic slot list (advanced) |

Prefer plain `WebComponent` + `slot()` for new code (clearer, matches `x_element.js`).

**See:** `examples/xelement_kit/.../shadow_dom.py`, `/slots/SlotsDemo`.

## Web Components (summary)

```
CustomElement  → light DOM   → x-tagname
WebComponent   → shadow DOM  → x-tagname + shadowroot|shadowdom
AlpineComponent→ + Alpine    → x-tagname + x-data
Runtime        → x_element.js
```

Full guide: [XELEMENT.md](XELEMENT.md).

## Browser coverage

```bash
# Static XElement fixture (no server)
node tests/browser/x_element_harness.mjs

# Live xelement_kit (pytest boots uvicorn)
python -m pytest tests/06_browser/test_kit_browser_deep.py -v
# or manually:
# KIT_URL=http://127.0.0.1:8766 node tests/browser/kit_browser_suite.mjs
```

Screenshots: `screenshots/kit/*.png` · report: `screenshots/kit/browser-report.json`

Covers: light DOM upgrade+click, shadow roots+slots, Alpine toggle, HTMX swap re-upgrade, slots demo, WC, Jinja, mobile viewport.
