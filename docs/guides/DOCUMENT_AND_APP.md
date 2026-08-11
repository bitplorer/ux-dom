# Document and App (superseded)

**Canonical:** [DOCUMENT.md](DOCUMENT.md) · [ARCHITECTURE.md](../internals/ARCHITECTURE.md)

`Document` is the HTML SSoT. `App` is an optional plugin hub registry only.
Prefer:

```python
document = Document(...).use(XElement(), Htmx(), Csp.auto())
app = FastAPI(...)
document.mount(app)
```
