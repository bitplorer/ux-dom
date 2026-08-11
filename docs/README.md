# ux-dom documentation

**Version 0.1.0** · **Start:** [START_HERE.md](START_HERE.md)

### Brand lines

| Layer | Name |
|-------|------|
| **PyPI / pip** | `ux-dom` |
| **Import** | `ux_dom` |
| **CLI** | **`uxdom`** |


---

## Feature map

| Doc | Purpose |
|-----|---------|
| **[FEATURES.md](FEATURES.md)** | **Complete feature encyclopedia** |

## Learning path

```text
START_HERE → INSTALL → guides/TUTORIAL → guides/DOCUMENT → guides/COMPONENTS
         → guides/XELEMENT → security/CSP → guides/COOKBOOK → internals/ARCHITECTURE
```

---

## Start

| Doc | Description |
|-----|-------------|
| [START_HERE.md](START_HERE.md) | Mental model + day-1 |
| [INSTALL.md](INSTALL.md) | Install & verify |

## Guides (`guides/`)

| Doc | Description |
|-----|-------------|
| [TUTORIAL.md](guides/TUTORIAL.md) | Scaffold to first page |
| [CLI.md](guides/CLI.md) | create-app, doctor, build |
| [DOCUMENT.md](guides/DOCUMENT.md) | Document SSoT |
| [DOCUMENT_TWO_STAGE.md](guides/DOCUMENT_TWO_STAGE.md) | Head/body stages |
| [COMPONENTS.md](guides/COMPONENTS.md) | Component / Fragment |
| [REACTIVE.md](guides/REACTIVE.md) | ReactiveComponent |
| [ROUTING.md](guides/ROUTING.md) | DirectoryRouter |
| [XELEMENT.md](guides/XELEMENT.md) | Custom elements |
| [XELEMENT_AUTO_DEFINITIONS.md](guides/XELEMENT_AUTO_DEFINITIONS.md) | Auto defs |
| [HYPERMEDIA.md](guides/HYPERMEDIA.md) | HTMX / Alpine / slots |
| [UI.md](guides/UI.md) | Optional UI kit |
| [COOKBOOK.md](guides/COOKBOOK.md) | Recipes |
| [DX.md](guides/DX.md) | DX principles |
| [API_SURFACE.md](guides/API_SURFACE.md) | Public vs private APIs |
| [APP_COMPOSITION.md](guides/APP_COMPOSITION.md) | App composition |
| [DOCUMENT_AND_APP.md](guides/DOCUMENT_AND_APP.md) | Document ↔ App |

## Security & assets (`security/`)

| Doc | Description |
|-----|-------------|
| [CSP.md](security/CSP.md) | Nonce CSP |
| [SAFE_STATIC.md](security/SAFE_STATIC.md) | Package static |
| [SCRIPT_INJECTION.md](security/SCRIPT_INJECTION.md) | Script inject / dedupe |
| [ASSETS.md](security/ASSETS.md) | WebAssets / Tailwind |
| [WHY_JS_URL.md](security/WHY_JS_URL.md) | Why JS needs a URL |

## Internals (`internals/`)

| Doc | Description |
|-----|-------------|
| [ARCHITECTURE.md](internals/ARCHITECTURE.md) | Layers & ownership |
| [DESIGN_CANON.md](internals/DESIGN_CANON.md) | **All design choices & intent** |
| [MODULE_MAP.md](internals/MODULE_MAP.md) | Every package path explained |
| [CONCEPTS.md](internals/CONCEPTS.md) | Core concepts |
| [CORE.md](internals/CORE.md) | Core surface |
| [RENDER_PHASES.md](internals/RENDER_PHASES.md) | Build vs serialize |
| [CONTEXT_SYNC_ASYNC.md](internals/CONTEXT_SYNC_ASYNC.md) | Context stacks |
| [MEMBERSHIP.md](internals/MEMBERSHIP.md) | Tree membership |
| [PRETTY_STREAM.md](internals/PRETTY_STREAM.md) | Pretty streaming |
| [CONCURRENCY.md](internals/CONCURRENCY.md) | Concurrency |
| [MEMORY_TREE.md](internals/MEMORY_TREE.md) | Memory / tree |

## Ship & maintain (`ship/`)

| Doc | Description |
|-----|-------------|
| [DEPLOY.md](ship/DEPLOY.md) | Deploy |
| [PRODUCTION_READINESS.md](ship/PRODUCTION_READINESS.md) | Checklist |
| [PUBLISHING.md](ship/PUBLISHING.md) | Release |
| [COVERAGE.md](ship/COVERAGE.md) | Coverage policy |
| [STABILITY.md](ship/STABILITY.md) | Stability |
| [CAPABILITIES.md](ship/CAPABILITIES.md) | Capability matrix |
| [MAINTENANCE_CANON.md](ship/MAINTENANCE_CANON.md) | Non-regression canon |
| [../CHANGELOG.md](../CHANGELOG.md) | Changelog |

## Archive

Historical audits live under [archive/](archive/) — not product docs.

## Tests

See [../tests/README.md](../tests/README.md) for the parallel test ontology.
