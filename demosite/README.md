# demosite — retired

This folder is a **frozen teaching snapshot**. It is **not** part of the
`ux_dom` package, not a product template, and not a library dependency.

**Greenfield path:** [ux-compose](https://github.com/bitplorer/ux-compose)

```bash
pip install ux-compose ux-dom
uxcompose create-app myapp --level 1
cd myapp && uxcompose serve dev
```

Compose already carries the teaching surface:

- `examples/` — Component / MorphState / overlays / forms / live ASGI
- `apps/atelier_shop` — shop Components on the product seat
- `apps/nook`, `apps/pulse` — product-shaped apps

Do not start a new app from this folder. Do not migrate these pages into
ux-dom. Leftover `DirectoryRouter` batteries in `ux_dom.routing` exist only
for `examples/` that cannot import compose.
