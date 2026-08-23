# Custom elements — organic API (single source of truth)

> **Diátaxis:** reference · **Canonical:** `docs/reference/XELEMENT_AUTO_DEFINITIONS.md` · **Layer:** ux-dom  
> Map: [INDEX.md](../INDEX.md).

## Mental model

| Concept | What you write |
|---------|----------------|
| **Class** | Definition (registered once in `xelement_registry`) |
| **Constructor** | Host only — `Hello()` → `<x-hello>` |
| **Document** | Auto-emits one `<template x-tagname>` per used class |

No `Definition()()` double call. No manual definitions list.

```python
class Hello(CustomElement):
    tag_name = "hello"  # optional; default = kebab-case class name

    def render(self, tag_name: str = "hello"):
        return template(div("Hi"), **{"x-tagname": tag_name})

# Page — hosts only
return document(
    div(Hello(), Hello(), Badge()),
    head=[title("Page")],
)
```

## Single source of truth

```text
xelement_registry
    Hello  →  definition Component  (built once on first Hello())
    Badge  →  definition Component

HtmlDocument.__pre_render__
    find hosts → host.xelement → registry definition
    dedupe by tag name → definitions slot in <body>
```

`Hello.definition()` returns the same object every time (advanced / tests).

## What not to do

```python
# Old / high cognitive load
d = Hello("hello")
host = d()

# Manual lists
div(d, host, className="hidden")  # unnecessary
```

## Shell

```python
document = Document(...).use(XElementRuntime(), ...)  # x_element.js
# from ux_dom.runtime import XElement as XElementRuntime alias
document.mount(app)
```

Note: `ux_dom.runtime.XElement` is the **runtime plugin** (JS file).  
`ux_dom.dom.htmlelement.CustomElement` is the **component base**.
