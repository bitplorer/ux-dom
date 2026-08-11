# Document ↔ App

## Design overview

**Document is the HTML SSoT.** “App” in everyday speech means the FastAPI
process plus your routes — not a second document factory.

```text
                    ┌──────────────┐
  request ─────────►│   FastAPI    │── routes / middleware / lifespan
                    └──────┬───────┘
                           │ document.mount(app)
                    ┌──────▼───────┐
                    │  Document    │── head/body · runtimes · static
                    └──────┬───────┘
                           │ document(*page)
                    ┌──────▼───────┐
                    │ Component    │── serialize → HTML / stream
                    │  tree        │
                    └──────────────┘
```

## Preferred pattern

```python
document = Document(...).use(XElement(), Htmx(), Csp.auto())
app = FastAPI(...)
document.mount(app)
# then DirectoryRouting(...).include(app) or explicit routes
```

## What `App` means in code

| Name | Meaning |
|------|---------|
| Everyday “app” | FastAPI instance + routes + Document |
| `ux_dom.plugins.App` | Optional plugin hub registry (tests / advanced) — **not** the HTML shell |
| `CreateAsgi` | Optional sugar; create-app uses plain FastAPI |

## Automation

Scaffold and keep composition via:

```bash
uxdom create-app myapp
uxdom doctor
```

Do not hand-reintroduce a parallel “App owns head/body” path.

**Canonical deep dives:** [DOCUMENT.md](DOCUMENT.md) · [APP_COMPOSITION.md](APP_COMPOSITION.md) ·
[ARCHITECTURE.md](../internals/ARCHITECTURE.md).
