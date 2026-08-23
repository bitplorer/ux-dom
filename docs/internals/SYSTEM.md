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
- Pure-dom CLI: `doctor` | `lint` | `build` | `profile` | `dashboard` | `add` | `ui`

## Does not own

| Concern | Home |
|---------|------|
| create-app / serve / deploy | **uxcompose only** |
| Host strategy / product App | ux-compose |
| HMR process | ux-compose (with serve) |
| Channel transport | ux-compose `wire/` |

## CLI

```bash
uxcompose create-app myapp
uxcompose serve app:asgi
uxcompose deploy --provider docker

uxdom doctor | lint | build | profile
```

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
