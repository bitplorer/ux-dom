# XElement guide — Light DOM & Shadow DOM

This is the **single** mental model for ux-dom custom elements.

## One contract

```
Python class     XElement / CustomElement / WebComponent / AlpineComponent
Definition attr  x-tagname="my-name"     ← only attribute for the name
Host tag         <x-my-name>
Browser file     x_element.js
Python helper    from ux_dom.scripts import x_element_js
```

Do **not** use `x-component` (removed from the contract).  
Do **not** ship multiple JS runtimes — only `x_element.js`.

## Definition vs host

| Step | Python | HTML shape |
|------|--------|------------|
| 1. Define once | `Widget("my-name")` | `<template x-tagname="my-name">…</template>` |
| 2. Use many times | `Widget("my-name")(*children)` | `<x-my-name>…</x-my-name>` |
| 3. Upgrade | load `x_element.js` | `customElements.define("x-my-name", …)` |

## Light DOM — `CustomElement`

**When:** page CSS, HTMX, simple composition.

**Rules:**

* `x-tagname` required  
* `shadowroot` / `shadowdom` **forbidden**

**Runtime:** clone template → **children of host**.

```python
from ux_dom.dom import div, template
from ux_dom.dom.htmlelement import CustomElement

class HelloLight(CustomElement):
    def render(self, tag_name: str = "hello-light"):
        return template(
            div("Hello from light DOM"),
            **{"x-tagname": tag_name},
        )

definition = HelloLight("hello-light")
host = definition()  # <x-hello-light>
```

Full gallery: `examples/xelement_kit` → `/lightdom/LightDomDemo`  
Source: `examples/xelement_kit/app/components/light_dom.py`

## Shadow DOM — `WebComponent`

**When:** encapsulation, slots, design-system widgets.

**Rules:**

* `x-tagname` required  
* `shadowroot="true"|"open"` **or** `shadowdom="open"|"closed"` required  

**Runtime:** `attachShadow` → clone template into shadow root.  
Light children of the host fill `<slot>` / `<slot name="…">`.

```python
from ux_dom.dom import div, slot, template
from ux_dom.dom.htmlelement import WebComponent

class ShellShadow(WebComponent):
    def render(self, tag_name: str = "shell-shadow"):
        return template(
            div(slot()),
            **{"x-tagname": tag_name, "shadowroot": "true"},
        )

host = ShellShadow("shell-shadow")("projected light child")
```

Full gallery: `/shadowdom/ShadowDomDemo`  
Source: `examples/xelement_kit/app/components/shadow_dom.py`

## Alpine — `AlpineComponent`

Requires **both** `x-tagname` and `x-data`. After upgrade, `x_element.js` calls `Alpine.initTree` when Alpine is on the page.

## Loading the runtime

```python
from ux_dom.dom import script
from ux_dom.scripts import x_element_js

# Prefer static file shipped by create-app:
script(src="/assets/js/x_element.js", defer=None)

# Or emit inline / save:
# script(x_element_js())
# x_element_js().save(file_or_dir=assets_js_dir)
```

`create-app` always writes `assets/js/x_element.js` and links it from `document.py`.

## Class hierarchy

```
Component
├── HTMLElement          # pass-through wrapper
├── AMPElement           # amp-* tags (unrelated)
├── AlpineElement        # requires x-data only
├── XElement             # requires x-tagname; host factory
│   ├── CustomElement    # light DOM (no shadow attrs)
│   ├── WebComponent     # shadow DOM (shadow attrs required)
│   └── AlpineComponent  # XElement + AlpineElement
├── JinjaElement
└── MarkdownElement
```

## Tests

* Unit / contract: `tests/test_xelement_runtime.py`
* Headless Chromium: `tests/test_xelement_browser.py` + `tests/browser/x_element_harness.mjs`
* create-app ships runtime: `tests/test_create_app_scaffold.py` / `tests/test_production_readiness.py`

## Related files

| Path | Role |
|------|------|
| `ux_dom/dom/htmlelement.py` | Python classes (documented) |
| `ux_dom/scripts/x_element.js` | Browser runtime |
| `ux_dom/scripts/__init__.py` | `x_element_js` helper |
| `examples/xelement_kit/` | Runnable demos |
| `docs/PRODUCTION_READINESS.md` | Release gates |


Also: [HYPERMEDIA.md](HYPERMEDIA.md) — Alpine, Jinja, HTMX, Slots coverage map.
