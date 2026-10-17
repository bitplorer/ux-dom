# XElement Kit: light DOM, shadow DOM, slots, htmx, Alpine

Custom elements defined in Python and upgraded in the browser by
`x_element.js`.

```bash
# from the repository root
uvicorn examples.xelement_kit.main:app --reload
# open http://127.0.0.1:8000
```

## Contract

| Python | Attribute(s) | Host tag | Runtime |
|--------|--------------|----------|---------|
| `XElement` | `x-tagname` | `x-{name}` | `x_element.js` |
| `CustomElement` | `x-tagname` only (no shadow) | `x-{name}` | light DOM |
| `WebComponent` | `x-tagname` + `shadowroot`/`shadowdom` | `x-{name}` | shadow DOM |
| `AlpineComponent` | `x-tagname` + `x-data` | `x-{name}` | + Alpine |

Construct the class to place a host (`HelloLight()`); the Document emits one
`<template x-tagname=...>` definition per class used on the page.

## Routes (`main.py`)

| Path | Page | Content |
|------|------|---------|
| `/` | `pages/index.py` | Index |
| `/lightdom` | `pages/lightdom.py` | Light DOM gallery and explanation |
| `/shadowdom` | `pages/shadowdom.py` | Shadow DOM gallery and slots |
| `/wc` | `pages/wc.py` | Short web-component demo |
| `/alpine` | `pages/alpine.py` | Alpine inside custom elements |
| `/htmx`, `/htmx/partial` | `pages/htmx.py` | htmx swap; new hosts upgrade automatically |
| `/jinja` | `pages/jinja.py` | Jinja `For`/`Var` expansion on the server |
| `/slots` | `pages/slots.py` | Named slots and `ux_dom.slots.Slots` |

## Wiring (`document.py`)

```python
document = Document(head=[...]).use(XElement(), Htmx(version="2.0.4"))
document.mount(app)   # serves /ux-dom/static/x_element.js from the package
```

* `x_element.js` is served from the installed package: one file, one URL
  (`ux_dom.runtime.XELEMENT_JS_URL`).
* htmx and Alpine are pinned with SRI.
* There is no `Csp` here: Alpine's standard build needs `'unsafe-eval'`. See
  `examples/showcase` for the strict-CSP setup.
* Tailwind comes from its play CDN for brevity (no SRI available); build CSS
  for production.

Tests: `tests/08_examples/test_xelement_kit.py` (HTTP) and
`tests/06_browser/test_kit_browser_deep.py` (Playwright).

Library docs: [`docs/reference/XELEMENT.md`](../../docs/reference/XELEMENT.md) ·
[`docs/reference/HYPERMEDIA.md`](../../docs/reference/HYPERMEDIA.md)
