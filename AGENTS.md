# Maintainer map (uxdom 0.1)

## Ownership (hard cut)

| Layer | Owns |
|-------|------|
| **ux-dom** | Render, Document shell, pure discovery, pure-dom CLI |
| **ux-compose** | Product create-app · serve · deploy · App · delivery · channel wire |

See [docs/internals/SYSTEM.md](docs/internals/SYSTEM.md) and ux-compose `docs/FLOW.md`.

## Single sources of truth

| Concern | Source |
|---------|--------|
| Browser files + tags | `Document.use` / contributions |
| Serialize | `__render__` / `__async_render__` |
| XElement runtime | `ux_dom/scripts/x_element.js` |
| Product scaffold | **uxcompose create-app** (not ux_dom.cli.scaffold) |
| Optional UI kit | `ux_dom/ui/*` (`uxdom add ui`) |

## Automation-first

| Need | Command |
|------|---------|
| New **product** app | `uxcompose create-app` |
| Component / XElement / UI | `uxdom add …` |
| Pure-dom integrity | `uxdom doctor` |
| Product health | `uxcompose doctor` |
| Quality | `sh scripts/quality.sh` |

## Package ontology

| Package | Role |
|---------|------|
| `ux_dom` | Document, Component, runtimes |
| `ux_dom.dom` | Tags / serialize |
| `ux_dom.runtime` | XElement, Htmx, Csp, Channel facades |
| `ux_dom.plugins` | Document contributions (not product App path) |
| `ux_dom.cli` | Pure-dom Typer CLI |
| `ux_dom.ui` | Optional kit |

## CLI spine

**Product:** `uxcompose create-app → serve → deploy`  
**Pure-dom:** `uxdom doctor | lint | build | profile | add`

## Tests

```bash
python -m pytest tests/ -q
```
