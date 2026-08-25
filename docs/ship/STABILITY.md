# Stability & brittle edges (0.1)

## Ownership

| Layer | CLI |
|-------|-----|
| **Product** lifecycle | `uxcompose create-app \| build \| serve \| deploy \| doctor` |
| **Pure-dom** tooling | `uxdom doctor \| lint \| profile \| add` |

## Hardened edges (render)

| Edge | Fix |
|------|-----|
| Dual JS names | Single `x_element.js` / `x-tagname` |
| Tailwind missing | product compile is `uxcompose build` (`ux_compose.tailwind`) |
| Page routes | Product discovery is `ux_compose.routing.DirectoryRoutes` |

## Stability gates

```bash
python -m pytest tests/ -q
uxdom doctor
uxcompose doctor .   # product apps
```

## Authoring rules

1. **XElement:** `x-tagname`; light vs shadow base classes.
2. **Product apps:** `uxcompose create-app` + routes under composition root.
3. **Document** serves library JS from package mount `/ux-dom/static/x_element.js`.

## DX surface (stable)

**uxcompose:** create-app · build · serve · deploy · doctor  
**uxdom:** doctor · lint · profile · dashboard · add · ui
