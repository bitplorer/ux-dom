# UxDom UI kit example

Shadcn-inspired components from `ux_dom.ui` — pure server HTML + Tailwind utilities.
Optional channel bridge documented in `docs/reference/UI.md`.

```bash
cd examples/ux_kit
PYTHONPATH=../..:.:$PYTHONPATH uvicorn app.main:app --port 8080 --reload
```

Or from repo root:

```bash
PYTHONPATH=.:examples/ux_kit uvicorn app.main:app --app-dir examples/ux_kit --port 8080
```
