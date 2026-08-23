# Stability & brittle edges (0.1)

## Ownership

| Layer | CLI |
|-------|-----|
| **Product** lifecycle | `uxcompose create-app \| serve \| deploy \| doctor` |
| **Pure-dom** tooling | `uxdom doctor \| lint \| build \| profile \| add` |

## Hardened edges (render / routing)

| Edge | Fix |
|------|-----|
| `route.py` + Component | DirectoryRouter discovers Components with `routes=` |
| Path params as query | Named path params in generated `get` |
| Nested packages | `_ensure_route_packages` writes `__init__.py` |
| Dual JS names | Single `x_element.js` / `x-tagname` |
| Tailwind missing | `cli/tailwind.py` resolver |

## Stability gates

```bash
python -m pytest tests/ -q
uxdom doctor
uxcompose doctor .   # product apps
```

## Authoring rules

1. **XElement:** `x-tagname`; light vs shadow base classes.
2. **Routes (pure-dom):** Components need `routes = ["get"]` + classmethod.
3. **Product apps:** `uxcompose create-app` + routes under composition root.
4. **Document** serves library JS from package mount `/ux-dom/static/x_element.js`.
5. Do not treat `plugins.App.web` or `FastAPIHost` as the product path.

## DX surface (stable)

**uxcompose:** create-app · serve · deploy · doctor  
**uxdom:** doctor · lint · build · profile · dashboard · add · ui
