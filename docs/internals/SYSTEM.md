# ux-dom System Boundary (hard cut)

> Companion to ux-compose `docs/FLOW.md`.

## One rule

**ux-dom renders. Product lifecycle is ux-compose only.**

```text
IN  → tag trees / Document / pure discovery helpers
OUT → HTML string | bytes | async token stream (+ Document shell)
```

## Owns

- Tag trees, `__render__` / `__async_render__`
- Document shell: control, runtime tags, **CSP stamp**, style
- Pure-dom CLI: `doctor` | `lint` | `profile` | `dashboard` | `add` | `ui`
- className, stylesheet `<link>`
- Package static (`/ux-dom/static/x_element.js`)

## Does not own

| Concern | Home |
|---------|------|
| create-app / build / serve / deploy | **uxcompose only** |
| Product page routes (`DirectoryRoutes`) | **ux-compose** |
| Tailwind compiler / app asset layout (`WebAssets`) | **ux-compose** |
| Host strategy / product App | ux-compose |
| HMR process / tunnel | ux-compose (with serve) |
| Channel transport | ux-compose `wire/` |

## CLI

```bash
uxcompose create-app myapp
uxcompose build
uxcompose serve app:asgi
uxcompose deploy --provider docker

uxdom doctor | lint | profile | add
```

## Document.use

Allowed: control, runtime, CSP, style.  
Not: HMR process, host strategy, product App.

## Forbidden residuals

- Dual product CLI on uxdom
- Product routing / host / HotReload living on ux-dom
- CSP stamp owned by host package
- FastAPI inside dunder serialize path
- App asset layout (`WebAssets`) on ux-dom
- Tailwind compiler (finder / `@source` / CLI invoke) on ux-dom
