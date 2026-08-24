# Changelog

## Unreleased

### Residual-free ownership (hard cut)

- **Product lifecycle is uxcompose only:** `create-app` / `build` / `serve` / `deploy`.
  `CreateProject.write()` raises `ProductScaffoldMoved`. `ux_dom.cli.scaffold`
  fails closed with a teaching import error. Doctor no longer runs scaffold
  integrity as if ux-dom owned product trees.
- **Product CSS:** `uxcompose build` (`ux_compose.tailwind` finds / downloads
  the CLI). `uxdom build` does **not** compile CSS. `TailwindCommand` /
  `TailwindStyle` / `ux_dom.cli.tailwind` fail closed and teach
  `uxcompose build`. `className`, Document `<link>`, and package static
  stay here. App folders are `ux_compose.WebAssets` (ux-dom `WebAssets` fails closed).
  Package-static dual-copy hatch is `serve="dual_copy"` (`serve="webassets"` leftover alias).
- **Preferred routing bind:** `DirectoryRoutes` + thin adapter.
  `DirectoryRouter` remains batteries-only for standalone FastAPI users.
- Historical `uxdom serve` / `create-app` notes below are **pre-cut**.

## Previously

### Next-style DX (`uxdom serve`)

- **`uxdom serve` / `dev` / `start`:** process runner matching Next `dev` / `start`.
  Standalone Tailwind CLI (PATH / pytailwindcss / cache / official download),
  Next-style `.env*` loading, `UXDOM_TAILWIND_OWNED` so Document `TailwindStyle`
  does not double-watch. `uxdom info` aliases `doctor`.
- **`--tunnel none|ngrok|cloudflare`:** health-gated public URL so the tunnel is
  never advertised against a dead origin (see [TUNNEL.md](docs/guides/TUNNEL.md)).
- **`TailwindCommand`** and **`uxdom build` / `doctor`** share `cli/tailwind.py`.
- Tests: `tests/03_routing_cli/test_serve_dx.py` (no download in CI).

### Channel-native design system

- **Tokens:** L0–L3 `surface`, `ink`, `type_scale`, `target` (`min-h-11`), `density`,
  `overlay`, `color`, `field_classes`.
- **Channel-first chrome:** Dialog / Sheet / Tabs / Carousel / Command / Popover /
  DropdownMenu — no Alpine `x-data` as the open/selected path. `open` / `active` /
  `index` are render arguments.
- **New markup:** Breadcrumb, Pagination, Kbd, EmptyState, PageHeader, StatusStrip,
  FormSection, RadioGroup, Progress, Sheet, Command, Popover, DropdownMenu.
- **DatePicker / Input:** elevated 44px `field_classes`; DatePicker keeps
  invalid / disabled / empty / min / max / required states.
- **Catalog:** new stems registered; Dialog/Tabs/Carousel runtime is Channel (none).
- Historical `Chart` + `channel_bridge` + `copy` + `catalog` stay in-tree.
- Tests lock no-`x-data` on elevated composites.

### UI kit battery (Phase 1)

- **Primitives:** `Slider` (native range, disabled/value). Checkbox invalid/disabled.
  Switch thumb + disabled. Table `TableCaption` / `TableEmpty` + `aria-sort`.
- **Composites:** `Carousel` (Alpine, empty state), `ToastHost` (morph-safe notices;
  server list is authority), `DatePicker` (native `type=date`), `Chart` (SVG
  sparkline/bar, no Chart.js).
- **Dialog a11y:** `role="dialog"`, `aria-modal`, labelled title.
- **Channel:** `public_form` progressive POST + optional Channel attrs.
- **Catalog / copy:** new stems registered; DatePicker copies Input.
- **Docs:** `docs/guides/UI.md` inventory + local-vs-authority table.
- Tests: `tests/02_document_plugins/test_ui_battery.py`.

### Completeness (2026-08-19)

- Chart tokens aligned to stone surfaces (leftover slate after the Channel-native restyle).
- UI kit comments, catalog, gallery copy, and UI.md use ux-behavior verbs
  (`open` / `close` / `select` / `notify`) instead of historical `open_overlay`.
- `uxdom build` import check puts the installed/source `ux_dom` on PYTHONPATH;
  import-error tails are no longer clipped to 300 characters.
- Unused `zip_recursive` stub removed.
- Catalog completeness test: every `ux_dom.ui` module is registered.

### Hardening

- **Tailwind scaffold without CLI:** `TailwindCommand` still writes v4 input CSS when
  `tailwindcss` is not on PATH (create-app / doctor layouts stay complete).
- **Single-copy messaging:** CLI `uxdom build` help + `docs/ship/DEPLOY.md` match
  package-mount `/ux-dom/static/x_element.js` (no dual-copy default).
- **Doc path integrity:** source/docs pointers use nested paths
  (`docs/guides/…`, `docs/security/…`, `docs/ship/…`); dead refs removed.
- **Gates:** `tests/04_production/test_docs_integrity.py` (markdown links, flat-path
  ban, single-copy messaging, XElement URL). `scripts/quality.sh` targets `src/ux_dom`.

### Docs / maintainership

- **Automation-first policy:** ceremonial app files default to `uxdom create-app` /
  `uxdom add`; hand-code only when extending features or making breaking changes
  ([DX.md](docs/guides/DX.md), [MAINTENANCE_CANON.md](docs/ship/MAINTENANCE_CANON.md) §5.5,
  [AGENTS.md](AGENTS.md)).
- **Freshness pass:** fixed nested doc links, full test package paths, archive index,
  package-mount XElement URL in [STABILITY.md](docs/ship/STABILITY.md).
- **Architecture overviews** at composition, routing, module map, design canon.

## 0.1.0 — ux-dom (first public line)

**Brand:** dist `ux-dom` · import `ux_dom` · CLI **`uxdom`** (unhyphenated).

Companion control plane: dist `ux-channel` · import `ux_channel` · CLI **`uxchannel`**.

| Surface | Value |
|---------|--------|
| Version | **0.1.0** |
| Document runtime | `.use` / `.mount`, XElement, Htmx, Csp, Channel |
| Control attrs | `.as_ux_dom()` (from ux-channel) |
| Static | `/ux-dom/static/x_element.js` (single-copy) |
| Wire (channel) | `data-channel-*`, `X-Channel-*` |

No shims for historical names (`uidom`, `ui_dom`, `ui-dom`).

### Architecture
- **Document** is the HTML shell source of truth
- Scaffold: FastAPI + `document.mount` + DirectoryRouting
- Concurrent tree locks; fail-closed reactive re-render

### Features
- `uxdom create-app` / `dev` / `doctor` / `add` / `build` / `deploy`
- XElement + `x_element.js`, DirectoryRouter `[id]` segments
- Nonce CSP, SafeStatic, streaming HTML, sync/async render
- ReactiveComponent (dataclass state + snapshot/rollback)

### Quality
- Ontological tests (`tests/01_core` … `06_browser`)
- Chaos / load / pentest batteries; browser harnesses

See [docs/START_HERE.md](docs/START_HERE.md) · [docs/ship/STABILITY.md](docs/ship/STABILITY.md).
