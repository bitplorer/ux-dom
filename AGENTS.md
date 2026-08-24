# AGENTS.md — ux-dom

Orientation for humans and agents continuing this package.

**First-time:** [START_HERE.md](START_HERE.md). **Map:** [docs/INDEX.md](docs/INDEX.md).

Read [START_HERE.md](START_HERE.md) then [docs/INDEX.md](docs/INDEX.md) then
[docs/internals/SYSTEM.md](docs/internals/SYSTEM.md).

## Layer ownership (hard cut)

The UX stack is a **layered system of specialists**, not a monolith.

| Layer | Owns | Must **not** own |
|-------|------|------------------|
| **ux-dom** (this repo) | HTML/CSS/JS trees, `Document`, serialize, pure discovery, `uxdom`, WebAssets *paths* | Intent, Cap, Result ops, MorphState, motion IR, product CLI, Tailwind CLI finder |
| **ux-channel** | Intent / Result / Cap / wire / peers / host runtime | HTML trees, CSS |
| **ux-behavior** | Product behavior, Morph/Ref, `@action`, validation | Raw HTML construction, wire codecs |
| **ux-motion** | Presence / transition plans as data (IR v1) | Product behavior, DOM construction |
| **ux-compose** | Author composition + product CLI (`uxcompose`) | Re-implementing any specialist |

Do not invent a sixth product (`ux-app` is retired; see ux-behavior `KILL_UX_APP.md`).
Do not analogize this layer to React / Next / htmx as its identity.

## Single sources of truth

| Concern | Source |
|---------|--------|
| Browser files + tags | `Document.use` / contributions |
| Serialize | `__render__` / `__async_render__` |
| XElement runtime | `ux_dom/scripts/x_element.js` → `/ux-dom/static/x_element.js` |
| Product scaffold | **`uxcompose create-app`** (not `ux_dom.cli.scaffold`) |
| Optional UI kit | `ux_dom/ui/*` (`uxdom add ui`) |
| Public names | `src/ux_dom/__init__.py` |
| Docs map | [docs/INDEX.md](docs/INDEX.md) |

## What not to invent

- Product CLI on `uxdom` (`create-app`, `serve`, `deploy`, product `build`)
- A second document factory on `App`
- Dual-copy of library JS into `assets/js/` (package URL is SSoT)
- Intent / Cap / Result types in this package
- Motion IR or Channel codecs
- Flat `docs/XELEMENT.md` (nested paths only; see `tests/04_production/test_docs_integrity.py`)

## Automation-first

| Need | Command |
|------|---------|
| New **product** app | `uxcompose create-app` |
| Product CSS minify | `uxcompose build` |
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

**Product:** `uxcompose create-app → build → serve → deploy`
**Pure-dom:** `uxdom doctor | lint | profile | add`
**CSS resolver:** `ux_compose.tailwind` (product). This package keeps `discover_css_io` as WebAssets path layout.

## Tests

```bash
python -m pytest tests/ -q
# docs links + nested-path law:
python -m pytest tests/04_production/test_docs_integrity.py -q
```

Broken relative markdown links are a defect. Archive is not citable as current law.
