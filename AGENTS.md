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

## Automation-first (ceremonial code)

**Default:** generate ceremonial / boring project files with CLI automation.
**Hand-code only** when extending features or making intentional breaking
changes to contracts.

| Need | Command |
|------|---------|
| New app | `uxdom create-app` |
| Component / route / XElement | `uxdom add …` |
| UI kit piece | `uxdom add ui` |
| Integrity | `uxdom doctor` |
| Quality | `sh scripts/quality.sh` |

Re-scaffold or regenerate with `--force` rather than maintaining diverged
boilerplate by hand. Core library code (`src/ux_dom/**`) is never “ceremonial”
— change it with tests + docs in the same PR.

Policy details: [docs/guides/DX.md](docs/guides/DX.md) ·
[docs/ship/MAINTENANCE_CANON.md](docs/ship/MAINTENANCE_CANON.md) §5.5.

## Layers

See [docs/internals/CONCEPTS.md](docs/internals/CONCEPTS.md) and
[docs/internals/ARCHITECTURE.md](docs/internals/ARCHITECTURE.md).

Design & implementation maps:

| Doc | Use when |
|-----|----------|
| [DESIGN_CANON.md](docs/internals/DESIGN_CANON.md) | Intent and non-negotiable choices |
| [MODULE_MAP.md](docs/internals/MODULE_MAP.md) | Where each package lives |
| [MAINTENANCE_CANON.md](docs/ship/MAINTENANCE_CANON.md) | Safe-touch map and regressions |
| [STABILITY.md](docs/ship/STABILITY.md) | Brittle edges and gates |

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

`create-app → serve / dev → add → doctor/lint → build [--package] → start / deploy`

## Keep docs fresh

- Product docs live under `docs/` with real subdirs (`guides/`, `internals/`,
  `security/`, `ship/`). Do not invent flat `docs/FOO.md` links for nested files.
- Tests live under `tests/01_core` … `tests/06_browser` — cite full paths.
- Historical notes go in `docs/archive/` only; never as the only SSoT for a
  current contract.
- When a §3 contract or CLI surface changes, update MAINTENANCE_CANON + the
  matching guide in the **same** change.

## Tests

```bash
python -m pytest tests/ -q
```

Layout: [tests/README.md](tests/README.md) — packages `01_core` … `06_browser`.

## Intentional non-bugs

- Dual `clean_attribute` (L0/L1 dialects)
- `[id]` path segments on disk
- No silent plugin autoload
