# Features (render layer)

> **Diátaxis:** reference · **Canonical:** `docs/reference/FEATURES.md` · **Layer:** ux-dom  
> Map: [INDEX.md](../INDEX.md).

ux-dom is the **hypermedia render** layer: trees → `__render__` / `__async_render__`, Document shell (control, runtime tags, CSP stamp), pure DirectoryRoutes.

## Product apps

```bash
uxcompose create-app myapp
uxcompose build
uxcompose serve app:asgi --port 8080
uxcompose deploy --provider docker
```

Composition, delivery, and product lifecycle live in **ux-compose**. See its
[FLOW law](https://github.com/bitplorer/ux-compose/blob/main/docs/FLOW.md).

## Pure Document tooling

```bash
uxdom doctor
uxdom lint
uxdom profile
```

Product CSS: `uxcompose build`.

## Core APIs

- `Document.use(...)` — shell contributions (control, runtime, CSP, style)
- `Component` / tags / `__render__` / `__async_render__`
- `routing.core.DirectoryRoutes` + `RouterHooks` (host-free discovery)

Product HTTP host strategy and HMR process: **ux-compose**, not Document.use.
