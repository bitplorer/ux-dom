# Cookbook

## Minimal Document + FastAPI

```python
from fastapi import FastAPI
from ux_dom import Document
from ux_dom.runtime import XElement, Htmx, Csp
from ux_dom.dom import div, h1

document = Document(ensure_csrf_token=False).use(
    XElement(), Htmx(), Csp.auto()
)
app = FastAPI()
document.mount(app)

@app.get("/")
def home():
    return document(div(h1("Hello")), page_title="Hi")
```

## Scaffold app

```bash
uxcompose create-app shop --host auto --level auto
cd shop && uxcompose serve app:asgi --port 8080
```

## HTMX partial

```python
button("Load", hx_get="/htmx_demo/Partial", hx_target="#panel", hx_swap="innerHTML")
# Partial.get returns fragment only — see ROUTING.md
```

## XElement light DOM

```python
from ux_dom.dom.htmlelement import CustomElement
from ux_dom.dom import div, template

class HelloLight(CustomElement):
    tag_name = "hello"
    def render(self, tag_name="hello"):
        return template(div("Hi"), **{"x-tagname": tag_name})

# In page: place host HelloLight() — Document auto-collects definition
```

See [XELEMENT.md](XELEMENT.md).

## CSP

```python
from ux_dom.runtime import Csp
document.use(Csp.auto())   # DEBUG → dev, else prod
# or Csp.prod() / Csp.dev() / Csp.report_only()
```

[CSP.md](../security/CSP.md)

## uxchannel ```python
from ux_dom.runtime import Channel
ch = Channel.optional(mount_via_ux_dom=False)
if ch:
    document.use(ch)
# attach channel app separately if needed
```

## Tailwind

Scaffold sets `WITH_TAILWIND` + `TailwindStyle` in lifespan.  
WebAssets: [ASSETS.md](../security/ASSETS.md).

## Streaming HTML

```python
from ux_dom.response.starlette import StreamingResponse, HTMLResponse
return HTMLResponse(document(div("x")))
# or StreamingResponse(tree) for chunked bodies
```

## Dataclass Component

```python
@dataclass(eq=False)
class Price(Component):
    amount: int
    def render(self, amount):
        return span(f"${amount}")
```

## Health check (scaffold)

`GET /health` → `{ ok, app, debug, csp, runtimes, … }`.


## Reactive counter

```python
from dataclasses import dataclass
from ux_dom import ReactiveComponent
from ux_dom.dom import div

@dataclass(eq=False)
class Counter(ReactiveComponent):
    count: int = 0
    def render(self, count=0):
        return div(f"{count}")
    def increment(self):
        self.count += 1
```
