# XElement Kit — Light DOM · Shadow DOM · HTMX · Alpine

Production-shaped examples for UxDom custom elements.

## Contract (memorize this)

| Python | Attribute(s) | Host tag | Runtime |
|--------|--------------|----------|---------|
| `XElement` | `x-tagname` | `x-{name}` | `x_element.js` |
| `CustomElement` | `x-tagname` only (no shadow) | `x-{name}` | light DOM |
| `WebComponent` | `x-tagname` + `shadowroot`/`shadowdom` | `x-{name}` | shadow DOM |
| `AlpineComponent` | `x-tagname` + `x-data` | `x-{name}` | + Alpine |

```python
from ux_dom.dom.htmlelement import CustomElement, WebComponent
from ux_dom.scripts import x_element_js  # → x_element.js
```

## Run

```bash
cd examples/xelement_kit
PYTHONPATH=../..:. uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

## Routes

| Path | Content |
|------|---------|
| `/lightdom/LightDomDemo` | **Full** Light DOM gallery + explanation |
| `/shadowdom/ShadowDomDemo` | **Full** Shadow DOM gallery + slots |
| `/wc/WcDemo` | Short WC smoke |
| `/alpine/AlpineDemo` | Alpine + XElement |
| `/htmx/HtmxDemo` | HTMX partial re-upgrade |
| `/jinja/JinjaDemo` | Jinja For/Var expansion |
| `/slots/SlotsDemo` | Named slots + `ux_dom.slots.Slots` |

## Code map

- `app/components/light_dom.py` — CustomElement examples (commented)
- `app/components/shadow_dom.py` — WebComponent examples (commented)
- `app/components/x_widgets.py` — mixed kit widgets
- Document serves **`/ux-dom/static/x_element.js`** via package mount (default)

Library docs: [`docs/reference/XELEMENT.md`](../../docs/reference/XELEMENT.md) ·
[`docs/reference/HYPERMEDIA.md`](../../docs/reference/HYPERMEDIA.md)
