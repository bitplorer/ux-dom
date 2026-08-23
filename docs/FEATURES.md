# Features (render layer)

ux-dom is the **hypermedia render** layer: trees → `__render__` / `__async_render__`, Document shell (control, runtime tags, CSP stamp), pure DirectoryRoutes.

## Product apps

```bash
uxcompose create-app myapp
uxcompose serve app:asgi --port 8080
uxcompose deploy --provider docker
```

Composition, delivery, and product lifecycle live in **ux-compose**. See its `docs/FLOW.md`.

## Pure Document tooling

```bash
uxdom doctor
uxdom lint
uxdom build
uxdom profile
```

## Core APIs

- `Document.use(...)` — shell contributions (control, runtime, CSP, style)
- `Component` / tags / `__render__` / `__async_render__`
- `routing.core.DirectoryRoutes` + `RouterHooks` (host-free discovery)

Product HTTP host strategy and HMR process: **ux-compose**, not Document.use.
