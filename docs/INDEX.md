# ux-dom documentation index

**Version 0.1.0**
**Start:** [../START_HERE.md](../START_HERE.md) · mental model: [START_HERE.md](START_HERE.md)

This file is the map. It does not replace the guides.

## Folder contract (Phase 2)

| Folder | Diátaxis mode | May contain | Must not contain |
|--------|---------------|-------------|------------------|
| `docs/guides/` | how-to | Goal-oriented recipes | Conceptual essays as primary form |
| `docs/reference/` | reference | Facts, signatures, tables | Learning narrative as primary form |
| `docs/internals/` | explanation | Why, architecture, C4 | Step lists as primary form |
| `docs/examples/` | examples | Worked recipes / pointers | Law |
| `docs/adr/` | ADR | Decisions (or an index of them) | Mixed how-to |

Specialized folders (`security/`, `ship/`, `design/`, `tutorial/`, `patterns/`, `archive/`) stay.
`docs/INDEX.md` is the map. Do not add a second competing map.

Old paths keep a 5-line stub. Do not cite stubs as canonical.

### Brand lines

| Layer | Name |
|-------|------|
| **PyPI / pip** | `ux-dom` |
| **Import** | `ux_dom` |
| **CLI** | **`uxdom`** (pure-dom) |
| **Product CLI** | **`uxcompose`** |

This layer **owns render**. It does not own Intent, Caps, Result ops, product
behavior, motion IR, or product lifecycle.

---

## Audience

| You are… | Start (≤ 2 clicks from repo root) |
|----------|-----------------------------------|
| **New** | [../START_HERE.md](../START_HERE.md) |
| **Pure Document / components** | [reference/DOCUMENT.md](reference/DOCUMENT.md) → [reference/COMPONENTS.md](reference/COMPONENTS.md) |
| **Product builder** | [ux-compose FLOW](https://github.com/bitplorer/ux-compose/blob/main/docs/FLOW.md) + [guides/TUTORIAL.md](guides/TUTORIAL.md) |
| **Maintainer** | [../AGENTS.md](../AGENTS.md) · [internals/SYSTEM.md](internals/SYSTEM.md) |
| **Agent** | [../AGENTS.md](../AGENTS.md) |

---

## By Diátaxis mode

### Tutorial

| Doc | Description |
|-----|-------------|
| [../START_HERE.md](../START_HERE.md) | 5-minute path |
| [START_HERE.md](START_HERE.md) | Mental model + day-1 (longer) |
| [guides/TUTORIAL.md](guides/TUTORIAL.md) | Product path + pure Document |

### How-to

| Doc | Description |
|-----|-------------|
| [../INSTALL.md](../INSTALL.md) · [INSTALL.md](INSTALL.md) | Install & verify |
| [guides/CLI.md](guides/CLI.md) | `uxdom` doctor · lint · build · add |
| [guides/COOKBOOK.md](guides/COOKBOOK.md) | Recipes |
| [guides/DX.md](guides/DX.md) | DX principles |
| [guides/TUNNEL.md](guides/TUNNEL.md) | Tunnel is **uxcompose**, not ux-dom |
| [examples/README.md](examples/README.md) | Example slot → repo `examples/` |
| [ship/DEPLOY.md](ship/DEPLOY.md) | Deploy notes |
| [ship/PUBLISHING.md](ship/PUBLISHING.md) | Publishing |
| [ship/TESTING.md](ship/TESTING.md) | Testing |

### Reference

| Doc | Description |
|-----|-------------|
| [reference/FEATURES.md](reference/FEATURES.md) | Feature encyclopedia |
| [reference/API_SURFACE.md](reference/API_SURFACE.md) | Public vs private APIs |
| [reference/DOCUMENT.md](reference/DOCUMENT.md) | Document SSoT |
| [reference/DOCUMENT_TWO_STAGE.md](reference/DOCUMENT_TWO_STAGE.md) | Head/body stages |
| [reference/COMPONENTS.md](reference/COMPONENTS.md) | Component / Fragment |
| [reference/REACTIVE.md](reference/REACTIVE.md) | ReactiveComponent |
| [reference/ROUTING.md](reference/ROUTING.md) | DirectoryRoutes + thin adapter |
| [reference/XELEMENT.md](reference/XELEMENT.md) | Custom elements |
| [reference/XELEMENT_AUTO_DEFINITIONS.md](reference/XELEMENT_AUTO_DEFINITIONS.md) | Auto defs |
| [reference/HYPERMEDIA.md](reference/HYPERMEDIA.md) | HTMX / Alpine / slots |
| [reference/UI.md](reference/UI.md) | Optional UI kit |
| [security/CSP.md](security/CSP.md) | Nonce CSP |
| [security/SAFE_STATIC.md](security/SAFE_STATIC.md) | Package static |
| [security/SCRIPT_INJECTION.md](security/SCRIPT_INJECTION.md) | Script injection |
| [security/ASSETS.md](security/ASSETS.md) | Asset policy |
| [security/WHY_JS_URL.md](security/WHY_JS_URL.md) | JS URL policy |
| [ship/CAPABILITIES.md](ship/CAPABILITIES.md) | Capabilities |
| [ship/STABILITY.md](ship/STABILITY.md) | Stability |
| [ship/COVERAGE.md](ship/COVERAGE.md) | Coverage |
| [reference/STACK.md](reference/STACK.md) | Stack map |
| [../CHANGELOG.md](../CHANGELOG.md) | History (not current teaching) |

### Explanation

| Doc | Description |
|-----|-------------|
| [internals/c4.md](internals/c4.md) | C4-style context / containers |
| [internals/SYSTEM.md](internals/SYSTEM.md) | Render boundary |
| [internals/ARCHITECTURE.md](internals/ARCHITECTURE.md) | Architecture |
| [internals/MODULE_MAP.md](internals/MODULE_MAP.md) | Module map |
| [internals/CONCEPTS.md](internals/CONCEPTS.md) | Concepts |
| [internals/CORE.md](internals/CORE.md) | Core |
| [internals/DESIGN_CANON.md](internals/DESIGN_CANON.md) | Design canon |
| [internals/RENDER_PHASES.md](internals/RENDER_PHASES.md) | Render phases |
| [internals/CONCURRENCY.md](internals/CONCURRENCY.md) | Concurrency |
| [internals/CONTEXT_SYNC_ASYNC.md](internals/CONTEXT_SYNC_ASYNC.md) | Context |
| [internals/MEMORY_TREE.md](internals/MEMORY_TREE.md) | Memory tree |
| [internals/MEMBERSHIP.md](internals/MEMBERSHIP.md) | Membership |
| [internals/PRETTY_STREAM.md](internals/PRETTY_STREAM.md) | Pretty stream |
| [internals/APP_COMPOSITION.md](internals/APP_COMPOSITION.md) | App composition |
| [internals/DOCUMENT_AND_APP.md](internals/DOCUMENT_AND_APP.md) | Document ↔ App |
| [ship/PRODUCTION_READINESS.md](ship/PRODUCTION_READINESS.md) | Production |
| [ship/MAINTENANCE_CANON.md](ship/MAINTENANCE_CANON.md) | Maintenance |
| [resilience/MATRIX.md](resilience/MATRIX.md) | Resilience matrix |

### Design / ADR

| Doc | Description |
|-----|-------------|
| [adr/README.md](adr/README.md) | ADR index |
| [adr/DESIGN_DECISIONS.md](adr/DESIGN_DECISIONS.md) | Design decisions |
| [adr/OWNERSHIP_COUNCIL.md](adr/OWNERSHIP_COUNCIL.md) | Ownership council |

---

## Archive (do not cite as current law)

| Doc | Note |
|-----|------|
| [archive/README.md](archive/README.md) | Historical audits / migration notes |

Dead names (must not reappear as live teaching): `docs/CONSISTENCY_REPORT.md`,
`docs/BUGS_AUDIT.md`, `MIGRATION_0.1.md`, `QUICKSTART.md`.

---

## Sister layers

| Package | Role |
|---------|------|
| [ux-channel](https://github.com/bitplorer/ux-channel) | Intent → Cap → Result |
| [ux-behavior](https://github.com/bitplorer/ux-behavior) | Product behavior → Ops |
| [ux-motion](https://github.com/bitplorer/ux-motion) | Presence / transition plans |
| [ux-compose](https://github.com/bitplorer/ux-compose) | Composition + product CLI |

Do not flatten these layers into this repo.

