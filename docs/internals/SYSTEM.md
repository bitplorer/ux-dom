# ux-dom System Boundary (hard cut)

> Companion to ux-compose `docs/FLOW.md`.

## One rule

**ux-dom renders. Product lifecycle is ux-compose only.**

```text
IN  → tag trees / Document / pure discovery
OUT → HTML string | bytes | async token stream (+ Document shell)
```

## Owns

- Tag trees, `__render__` / `__async_render__`
- Document shell: control, runtime tags, **CSP stamp**, style
- Pure DirectoryRoutes + RouterHooks
- Pure-dom CLI: `doctor` | `lint` | `profile` | `dashboard` | `add` | `ui`
- WebAssets *paths* (where CSS/JS files sit). className. stylesheet `<link>`.

## Does not own

| Concern | Home |
|---------|------|
| create-app / build / serve / deploy / Tailwind CLI finder | **uxcompose only** |
| Host strategy / product App | ux-compose |
| HMR process | ux-compose (with serve) |
| Channel transport | ux-compose `wire/` |

## CLI

```bash
uxcompose create-app myapp
uxcompose build
uxcompose serve app:asgi
uxcompose deploy --provider docker

uxdom doctor | lint | profile | add
```

`uxdom build` remains Document/static verify for leftover `app/main.py`
trees — not the product CSS command.

## Document.use

Allowed: control, runtime, CSP, style.  
Not: HMR process, FastAPIHost, product App.

## Plugins

`plugins.App` / `PluginHub` / `plugins.host` are **not** the product path.
Product composition root: **ux_compose.App** / `build()`.

## Forbidden residuals

- Dual product CLI on uxdom
- Recommending plugins.App.web as app entry
- CSP stamp owned by host package
- FastAPI inside dunder serialize path
