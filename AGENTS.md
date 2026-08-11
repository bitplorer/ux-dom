# Maintainer map (uxdom 0.1)

## Single sources of truth

| Concern | Source |
|---------|--------|
| Browser files + tags | `Document.use` / plugin contributions |
| Static on disk | hub materialize / `uxdom build` |
| Document inject | `shell_fragments` / Document common_* |
| XElement runtime | `ux_dom/scripts/x_element.js` via `XElement` / `x_element_js` |
| Scaffold | `ux_dom/cli/scaffold.py` |
| Optional UI kit | `ux_dom/ui/*` (`uxdom add ui`) |

**Do not** reintroduce a parallel asset registry. `ux_dom.assets` is a thin facade over the hub.

## Layers

See [docs/internals/CONCEPTS.md](docs/internals/CONCEPTS.md) and [docs/internals/ARCHITECTURE.md](docs/internals/ARCHITECTURE.md).

## Package ontology

| Package | Role |
|---------|------|
| `ux_dom` | Public entry: Document, Component, runtimes |
| `ux_dom.dom` | Tags / Component / parse / serialize |
| `ux_dom.runtime` | Document-facing XElement, Htmx, Csp, Channel |
| `ux_dom.plugins` | Host, routing, style, CSP, hub |
| `ux_dom.response` | HTML / streaming adapters |
| `ux_dom.scripts` | `x_element.js` only (no legacy aliases) |
| `ux_dom.cli` | Typer CLI |
| `ux_dom.ui` | Optional component kit |

## CLI spine

`create-app → dev → add → doctor/lint → build [--package] → deploy`

## Tests

```bash
python -m pytest tests/ -q
```

Layout: [tests/README.md](tests/README.md) — packages `01_core` … `06_browser`.

## Intentional non-bugs

- Dual `clean_attribute` (L0/L1 dialects)
- `[id]` path segments on disk
- No silent plugin autoload
