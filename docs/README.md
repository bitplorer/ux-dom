# ux-dom documentation

**Version 0.1.0** · **Start:** [../START_HERE.md](../START_HERE.md) · **Map:** [INDEX.md](INDEX.md)
GitHub renders this file when you open `docs/`. The Diátaxis audience+mode map is [INDEX.md](INDEX.md).

### Brand lines

| Layer | Name |
|-------|------|
| **PyPI / pip** | `ux-dom` |
| **Import** | `ux_dom` |
| **CLI** | **`uxdom`** |

This layer **renders**. Product lifecycle is **ux-compose**.

---

## Feature map

| Doc | Purpose |
|-----|--------|
| **[FEATURES.md](FEATURES.md)** | **Complete feature encyclopedia** |
| **[INDEX.md](INDEX.md)** | **Audience + Diátaxis map of every remaining doc** |

## Audiences

| You are… | Start |
|----------|--------|
| **New to ux-dom** | [../START_HERE.md](../START_HERE.md) |
| **Building product apps** | [ux-compose FLOW](https://github.com/bitplorer/ux-compose/blob/main/docs/FLOW.md) + [guides/TUTORIAL.md](guides/TUTORIAL.md) |
| **Pure Document / components** | [guides/DOCUMENT.md](guides/DOCUMENT.md) → [guides/COMPONENTS.md](guides/COMPONENTS.md) |
| **Maintainer / architecture** | [internals/SYSTEM.md](internals/SYSTEM.md) · [internals/ARCHITECTURE.md](internals/ARCHITECTURE.md) |
| **Contributor / agent** | [../CONTRIBUTING.md](../CONTRIBUTING.md) · [../AGENTS.md](../AGENTS.md) |

## Learning path

```text
START_HERE → INSTALL → guides/TUTORIAL → guides/DOCUMENT → guides/COMPONENTS
         → guides/XELEMENT → security/CSP → guides/COOKBOOK → internals/ARCHITECTURE
```

Diátaxis grouping (tutorial / how-to / reference / explanation): **[INDEX.md](INDEX.md)**.

---

## Start

| Doc | Description |
|-----|-------------|
| [../START_HERE.md](../START_HERE.md) | 5-minute path (root) |
| [START_HERE.md](START_HERE.md) | Mental model + day-1 |
| [INSTALL.md](INSTALL.md) | Install & verify |

## Guides (`guides/`)

| Doc | Description |
|-----|-------------|
| [TUTORIAL.md](guides/TUTORIAL.md) | Product path + pure Document |
| [CLI.md](guides/CLI.md) | pure-dom doctor · lint · build · add |
| [DOCUMENT.md](guides/DOCUMENT.md) | Document SSoT |
| [DOCUMENT_TWO_STAGE.md](guides/DOCUMENT_TWO_STAGE.md) | Head/body stages |
| [COMPONENTS.md](guides/COMPONENTS.md) | Component / Fragment |
| [REACTIVE.md](guides/REACTIVE.md) | ReactiveComponent |
| [ROUTING.md](guides/ROUTING.md) | DirectoryRoutes + thin adapter |
| [XELEMENT.md](guides/XELEMENT.md) | Custom elements |
| [XELEMENT_AUTO_DEFINITIONS.md](guides/XELEMENT_AUTO_DEFINITIONS.md) | Auto defs |
| [HYPERMEDIA.md](guides/HYPERMEDIA.md) | HTMX / Alpine / slots |
| [UI.md](guides/UI.md) | Optional UI kit |
| [COOKBOOK.md](guides/COOKBOOK.md) | Recipes |
| [DX.md](guides/DX.md) | DX principles |
| [API_SURFACE.md](guides/API_SURFACE.md) | Public vs private APIs |
| [APP_COMPOSITION.md](guides/APP_COMPOSITION.md) | App composition |
| [DOCUMENT_AND_APP.md](guides/DOCUMENT_AND_APP.md) | Document ↔ App |
| [TUNNEL.md](guides/TUNNEL.md) | Tunnel is uxcompose, not ux-dom |

## Security & assets (`security/`)

| Doc | Description |
|-----|-------------|
| [CSP.md](security/CSP.md) | Nonce CSP |
| [SAFE_STATIC.md](security/SAFE_STATIC.md) | Package static |
| [SCRIPT_INJECTION.md](security/SCRIPT_INJECTION.md) | Script injection |
| [ASSETS.md](security/ASSETS.md) | Asset policy |
| [WHY_JS_URL.md](security/WHY_JS_URL.md) | JS URL policy |

## Internals (`internals/`)

| Doc | Description |
|-----|-------------|
| [SYSTEM.md](internals/SYSTEM.md) | Render boundary |
| [ARCHITECTURE.md](internals/ARCHITECTURE.md) | Architecture |
| [MODULE_MAP.md](internals/MODULE_MAP.md) | Module map |
| [CONCEPTS.md](internals/CONCEPTS.md) | Concepts |
| [CORE.md](internals/CORE.md) | Core |
| [DESIGN_CANON.md](internals/DESIGN_CANON.md) | Design canon |
| [RENDER_PHASES.md](internals/RENDER_PHASES.md) | Render phases |
| [CONCURRENCY.md](internals/CONCURRENCY.md) | Concurrency |
| [CONTEXT_SYNC_ASYNC.md](internals/CONTEXT_SYNC_ASYNC.md) | Context |
| [MEMORY_TREE.md](internals/MEMORY_TREE.md) | Memory tree |
| [MEMBERSHIP.md](internals/MEMBERSHIP.md) | Membership |
| [PRETTY_STREAM.md](internals/PRETTY_STREAM.md) | Pretty stream |

## Ship (`ship/`)

| Doc | Description |
|-----|-------------|
| [CAPABILITIES.md](ship/CAPABILITIES.md) | Capabilities |
| [TESTING.md](ship/TESTING.md) | Testing |
| [STABILITY.md](ship/STABILITY.md) | Stability |
| [PRODUCTION_READINESS.md](ship/PRODUCTION_READINESS.md) | Production |
| [PUBLISHING.md](ship/PUBLISHING.md) | Publishing |
| [DEPLOY.md](ship/DEPLOY.md) | Deploy |
| [COVERAGE.md](ship/COVERAGE.md) | Coverage |
| [MAINTENANCE_CANON.md](ship/MAINTENANCE_CANON.md) | Maintenance |

## Stack & design

| Doc | Description |
|-----|-------------|
| [STACK.md](STACK.md) | Stack map |
| [FEATURES.md](FEATURES.md) | Feature encyclopedia |
| [resilience/MATRIX.md](resilience/MATRIX.md) | Resilience matrix |
| [design/DESIGN_DECISIONS.md](design/DESIGN_DECISIONS.md) | Design decisions |
| [design/OWNERSHIP_COUNCIL.md](design/OWNERSHIP_COUNCIL.md) | Ownership council |
| [archive/README.md](archive/README.md) | Historical (do not cite as law) |
