# ux-dom — snippets

> **Diátaxis:** how-to · copy-paste patterns from the public API (`__all__` / CLI).
> Map: see this package `docs/INDEX.md`.

Render layer. Trees serialize with __render__. Document is the shell. Product serve is uxcompose.

Every block is meant to run (or to be the exact fragment you drop into a running app). Names are public exports. If code and this page disagree, **code wins**.

**12 snippets** covering install, core usage, CLI, and the usage patterns that keep layers from leaking.

### Public names in this cookbook

`Document`, `Component`, `XElement`, `Htmx`, `Csp`, `div`, `h1`, `p`, `button`, `section`, `h2`, `ul`, `li`, `Fragment`, `span`, `dataclass`, `ReactiveComponent`, `Button`, `Card`, `CardHeader`, `CardTitle`, `CardContent`

## Contents

- [Install](#dom-install)
- [Document shell + serialize](#dom-document)
- [Component / Fragment](#dom-component)
- [Nonce CSP stamp](#dom-csp)
- [Fragment fans attrs onto children](#dom-fragment)
- [ReactiveComponent re-renders on field change](#dom-reactive)
- [Optional UI kit (Button / Card)](#dom-ui-kit)
- [XElement + Htmx contributions](#dom-htmx)
- [Page routes (product — ux-compose)](#dom-routes)
- [Pure-dom CLI](#dom-cli)
- [Copy-in UI kit via CLI](#dom-add-ui)
- [Pattern: __render__ is the serialize SSoT](#dom-pattern-serialize)


## Install

### Install

<a id="dom-install"></a>

Full stack requires Python ≥ 3.14. Product create-app / build / serve live on uxcompose, not uxdom.

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

### Fragment fans attrs onto children

<a id="dom-fragment"></a>

Fragment is a transparent group. Unique attrs (id) apply only to the first child so you never emit duplicate ids.

```python
from ux_dom import Fragment
from ux_dom.dom import div, span

tree = Fragment(className="row")(
    span("A"),
    span("B"),
)
print(tree.__render__())
# class="row" is applied to each child. id= would apply only to the first child.
```

### ReactiveComponent re-renders on field change

<a id="dom-reactive"></a>

render() runs before the old tree is cleared — an exception leaves the previous tree intact. This is still render, not MorphState.

```python
from dataclasses import dataclass
from ux_dom import ReactiveComponent
from ux_dom.dom import div, button

@dataclass(eq=False)
class Counter(ReactiveComponent):
    count: int = 0

    def render(self, count=0):
        return div(str(self.count), id="n")

    def increment(self):
        self.count += 1

c = Counter(count=1)
c.increment()
print("2" in str(c))
```

### Optional UI kit (Button / Card)

<a id="dom-ui-kit"></a>

Markup + tokens only. No Op construction. Copy into the app with: uxdom add ui Button. Live morph is ux-behavior / ux-channel.

```python
from ux_dom.ui import Button, Card, CardHeader, CardTitle, CardContent

card = Card(
    CardHeader(CardTitle("Cart")),
    CardContent(Button("Add", variant="default", size="md", type="button")),
)
print(card.render().__render__())
```

### XElement + Htmx contributions

<a id="dom-htmx"></a>

Document.use stamps contributions. HTMX is never auto-attached by ux-compose; opt in here. Product serve stays on uxcompose.

```python
from ux_dom import Document
from ux_dom.runtime import XElement, Htmx, Csp
from ux_dom.dom import div

document = Document(head=[], body=[]).use(
    XElement(),
    Htmx(),
    Csp.auto(),
)
html = document(div("Hi", id="view")).__render__()
print("script" in html.lower() or "csp" in html.lower() or html)
```

### Page routes (product — ux-compose)

<a id="dom-routes"></a>

Page-unit discovery is not a ux-dom API. Product apps use:

```python
from ux_compose.routing import DirectoryRoutes, RouterHooks
# or: ux_compose.build(...) / App.mount / uxcompose serve
```

See ux-compose `docs/guides/SNIPPETS.md` and `docs/FLOW.md`.


## CLI

### Pure-dom CLI

<a id="dom-cli"></a>

uxdom is Document tooling only. uxcompose create-app | build | serve | deploy is the product path.

```bash
uxdom doctor
uxdom lint
uxdom profile
uxdom add component Card
```

Product CSS minify is `uxcompose build` (`ux_compose.tailwind`).

### Copy-in UI kit via CLI

<a id="dom-add-ui"></a>

uxdom add copies markup you own. uxcompose create-app | build | serve | deploy remains the product path.

```bash
uxdom ui list
uxdom add ui Button
uxdom add component Card
uxdom doctor
uxdom lint
uxdom profile
```


## Usage patterns

### Pattern: __render__ is the serialize SSoT

<a id="dom-pattern-serialize"></a>

Serialize SSoT is tree.__render__() / tree.__async_render__(). Product create-app / build / serve is uxcompose, not uxdom.

```python
from ux_dom.dom import div, h1, p

tree = div(h1("Shop"), p("Server-authored HTML."), id="view")
html = tree.__render__()          # SSoT
# html = tree.__async_render__()  # async variant
print(html)
# str(tree) may work for debugging; do not treat it as the wire contract.
```
