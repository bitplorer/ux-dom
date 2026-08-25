# Maintenance canon (ux-dom)

## Safe-touch map

| Area | Touch with |
|------|------------|
| Core DOM / Document / dunders | Tests + SYSTEM.md |
| Pure-dom CLI (doctor/lint/build) | tests + CLI.md |
| Product scaffold / build / serve / deploy | **ux-compose** — not this repo |
| CSP stamp | Document contributions |

## Must not regress

1. Serialize SSoT remains `__render__` / `__async_render__`.
2. Product authors are not steered to `uxdom create-app` or `plugins.App.web`.
3. Package static JS single-copy model (`/ux-dom/static/x_element.js`).
4. DirectoryRoutes host-free path law.

## Scaffold / deploy

```text
Product scaffold  →  uxcompose create-app
Product deploy    →  uxcompose deploy
Pure-dom health   →  uxdom doctor
Routes (product)  →  ux-compose routes/ + App.mount
```

## Gates

```bash
python -m pytest tests/ -q
uxdom doctor
```
