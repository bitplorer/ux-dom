# DX map

> **Diátaxis:** how-to · **Canonical:** `docs/guides/DX.md` · **Layer:** ux-dom  
> Map: [INDEX.md](../INDEX.md).

## Product (uxcompose only)

| Need | Command |
|------|---------|
| Scaffold | `uxcompose create-app` |
| CSS minify | `uxcompose build` |
| Run | `uxcompose serve app:asgi` |
| Deploy configs | `uxcompose deploy` |
| Product health | `uxcompose doctor` |

## Pure Document (uxdom)

| Need | Command |
|------|---------|
| Env / package health | `uxdom doctor` |
| Conventions | `uxdom lint` |
| Render p95 | `uxdom profile` / `dashboard` |
| Component stubs | `uxdom add component\|ui\|xelement` |
| Document/static verify (`app/main.py` trees) | `uxdom build` |

Tailwind compiler: `ux_compose.tailwind`. App folders: `ux_compose.WebAssets`.
Product command: `uxcompose build`.

See `docs/guides/CLI.md` and ux-compose `docs/FLOW.md`.
