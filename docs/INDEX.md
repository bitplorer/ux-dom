# ux-dom documentation index

**Version 0.1.0**
**Start:** [../START_HERE.md](../START_HERE.md) · mental model: [START_HERE.md](START_HERE.md)

This file is the map. It does not replace the guides.

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
| **Pure Document / components** | [guides/DOCUMENT.md](guides/DOCUMENT.md) → [guides/COMPONENTS.md](guides/COMPONENTS.md) |
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
| [ship/DEPLOY.md](ship/DEPLOY.md) | Deploy notes |
| [ship/PUBLISHING.md](ship/PUBLISHING.md) | Publishing |
| [ship/TESTING.md](ship/TESTING.md) | Testing |

### Reference

| Doc | Description |
|-----|-------------|
| [FEATURES.md](FEATURES.md) | Feature encyclopedia |
| [guides/API_SURFACE.md](guides/API_SURFACE.md) | Public vs private APIs |
| [guides/DOCUMENT.md](guides/DOCUMENT.md) | Document SSoT |
| [guides/DOCUMENT_TWO_STAGE.md](guides/DOCUMENT_TWO_STAGE.md) | Head/body stages |
| [guides/COMPONENTS.md](guides/COMPONENTS.md) | Component / Fragment |
| [guides/REACTIVE.md](guides/REACTIVE.md) | ReactiveComponent |
| [guides/ROUTING.md](guides/ROUTING.md) | DirectoryRoutes + thin adapter |
| [guides/XELEMENT.md](guides/XELEMENT.md) | Custom elements |
| [guides/XELEMENT_AUTO_DEFINITIONS.md](guides/XELEMENT_AUTO_DEFINITIONS.md) | Auto defs |
| [guides/HYPERMEDIA.md](guides/HYPERMEDIA.md) | HTMX / Alpine / slots |
| [guides/UI.md](guides/UI.md) | Optional UI kit |
| [security/CSP.md](security/CSP.md) | Nonce CSP |
| [security/SAFE_STATIC.md](security/SAFE_STATIC.md) | Package static |
| [security/SCRIPT_INJECTION.md](security/SCRIPT_INJECTION.md) | Script injection |
| [security/ASSETS.md](security/ASSETS.md) | Asset policy |
| [security/WHY_JS_URL.md](security/WHY_JS_URL.md) | JS URL policy |
| [ship/CAPABILITIES.md](ship/CAPABILITIES.md) | Capabilities |
| [ship/STABILITY.md](ship/STABILITY.md) | Stability |
| [ship/COVERAGE.md](ship/COVERAGE.md) | Coverage |
| [STACK.md](STACK.md) | Stack map |
| [../CHANGELOG.md](../CHANGELOG.md) | History (not current teaching) |

### Explanation

| Doc | Description |
|-----|-------------|
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
| [guides/APP_COMPOSITION.md](guides/APP_COMPOSITION.md) | App composition |
| [guides/DOCUMENT_AND_APP.md](guides/DOCUMENT_AND_APP.md) | Document ↔ App |
| [ship/PRODUCTION_READINESS.md](ship/PRODUCTION_READINESS.md) | Production |
| [ship/MAINTENANCE_CANON.md](ship/MAINTENANCE_CANON.md) | Maintenance |
| [resilience/MATRIX.md](resilience/MATRIX.md) | Resilience matrix |

### Design / ADR

| Doc | Description |
|-----|-------------|
| [design/DESIGN_DECISIONS.md](design/DESIGN_DECISIONS.md) | Design decisions |
| [design/OWNERSHIP_COUNCIL.md](design/OWNERSHIP_COUNCIL.md) | Ownership council |

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

