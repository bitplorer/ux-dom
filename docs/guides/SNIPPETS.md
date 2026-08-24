# ux-dom — snippets

> **Diátaxis:** how-to · copy-paste patterns from the public API (`__all__` / CLI).
> Map: see this package `docs/INDEX.md`.

Render layer. Trees serialize with __render__. Document is the shell. Product serve is uxcompose.

Every block is meant to run (or to be the exact fragment you drop into a running app). Names are public exports. If code and this page disagree, **code wins**.

## Contents

- [Install](#dom-install)
- [Document shell + serialize](#dom-document)
- [Component / Fragment](#dom-component)
- [Pure-dom CLI](#dom-cli)
- [Nonce CSP stamp](#dom-csp)

## Install

### Install

<a id="dom-install"></a>

Full stack requires Python ≥ 3.14. Product create-app / serve live on uxcompose, not uxdom.

```bash
python3.14 -m venv .venv && source .venv/bin/activate
pip install ux-dom
uxdom doctor
```

## Core usage

### Document shell + serialize

<a id="dom-document"></a>

Serialize SSoT is tree.__render__() / tree.__async_render__(). Document.use stamps control, runtime, CSP — not HMR or product serve.

```python
from ux_dom import Document, Component
from ux_dom.runtime import XElement, Htmx, Csp
from ux_dom.dom import div, h1, p, button, section

document = Document(head=[], body=[]).use(
    XElement(),
    Htmx(),
    Csp.auto(),
)

html = document(
    section(
        h1("Shop"),
        p("Server-authored HTML."),
        button("Add", type="button"),
        id="view",
    )
).__render__()
print(html)
```

### Component / Fragment

<a id="dom-component"></a>

Components build trees. They do not dispatch Intents or MorphState — that is ux-behavior / ux-compose.

```python
from ux_dom import Component
from ux_dom.dom import div, h2, ul, li

class ProductList(Component):
    def __init__(self, titles: list[str]):
        self.titles = titles

    def render(self):
        return div(
            h2("Catalog"),
            ul(*[li(t) for t in self.titles]),
            id="catalog",
        )

print(ProductList(["Tee", "Tote"]).render().__render__())
```

## CLI

### Pure-dom CLI

<a id="dom-cli"></a>

uxdom is Document tooling only. uxcompose create-app | serve | deploy is the product path.

```bash
uxdom doctor
uxdom lint
uxdom build
uxdom profile
uxdom add component Card
```

## Core usage

### Nonce CSP stamp

<a id="dom-csp"></a>

CSP is a Document.use contribution. See docs/security/CSP.md. Do not inline event handlers.

```python
from ux_dom.runtime import Csp
from ux_dom import Document
from ux_dom.dom import div

document = Document(head=[], body=[]).use(Csp.auto())
html = document(div("ok")).__render__()
# Look for nonce= on script tags and a Content-Security-Policy meta/header stamp.
```
