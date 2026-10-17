# Changelog

## 0.3.0 — 2026-10-17 — secure defaults, leftover cleanup

### Security (BREAKING)

- **Strings are text.** `Fragment("...")` and a `str` returned from
  `Component.render()` are escaped. Before, they were parsed as HTML through
  a deny-list that let `x-init`, `@click`, `hx-on`, `hx-get`, `<style>` and
  `<form>` through. Opt in to markup with `markupsafe.Markup` (any
  `__html__`). See `docs/security/HTML_CONTENT.md`.
- **`defHTML(s)` is an allow-list sanitizer**: formatting tags and a small
  attribute list survive; scripts, styles, forms, custom elements, `on*`,
  `x-*`, `@*`, `:*`, `hx-*`, `data-*` and `style` are dropped with their
  content; URLs go through `safe_attr_value`. `defHTML(s, escape=False)`
  still parses author markup verbatim. Parser no longer drops entities
  (`a &amp; b`) or spaces between inline words.
- **`MarkdownElement` escapes raw HTML** and sanitizes its output; subclass
  with `escape_string = False` for trusted Markdown.
- **htmx request URLs are same-origin.** `hx-get/post/put/patch/delete`,
  `sse-connect` and `ws-connect` accept relative URLs only; wrap a URL in
  `cross_origin(url)` to allow another origin.
- **Pinned CDN scripts with SRI.** `HtmxControl` emits exact htmx 1.9.12 /
  2.0.4, SSE extension and idiomorph 0.8.0 URLs with `integrity` and
  `crossorigin="anonymous"`. Another `version=` with `cdn=True` raises
  `ValueError`; `sse_version=` was removed. The dev CSP lists those exact
  files instead of whole CDN hosts.

### Removed (BREAKING, no shims: ux-dom is unpublished)

- Leftover `DirectoryRouter` (`ux_dom.routing`, `ux_dom.plugins.routing`),
  hub routing, `App.routes`, `Component.__getattribute__` verb proxy,
  `uxdom add route`, the router lint rule. Page routing is
  `ux_compose.routing.DirectoryRoutes`. Explicit FastAPI routes can use the
  new `ux_dom.response.fastapi.HTMLRoute` / `StreamingRoute`.
- `ux_dom.assets` compat facade (`sync_assets` and five helpers).
- `csstags` / `StyleTags` (CSS rendered with HTML URL rules, no CSS escaping).
- `dom_util.system` (shell=True), `include`, `lazy` (unescaped),
  `unescape`, `url_escape`, `url_unescape`; `ux_dom.dom.icons` (68 icon trees
  built at import time); `ux_dom.examples`, `dom/src/ws_rpc.py`,
  `utils/functional.py`, `settings/paths.py`, `cli/envfile.py`, watchgod
  reloader branch; Python 2 shims and dead import fallbacks; commented-out code.
- `examples/with_ux_channel`, `demosite`, `examples/ux_dom_only/hypermedia_shop`.
  The ux-channel + ux-dom example lives in ux-channel.

### Changed

- One attribute serializer (`dom_util.iter_attributes`) for `dom_tag` and
  `ext.Tags` (fixes `hidden=None` rendering `hidden="None"`).
- Channel bridge builds attrs with `ux_channel` `ControlAttrs`, escapes once,
  no blanket `except`.
- valio PEP 649 patch is applied lazily by `ux_dom.elements`, not on
  `import ux_dom`.
- `ux_dom` has an explicit `__all__`; `PackagedFile.public_path_webassets` →
  `public_path_under_assets`; build manifest key `webassets_copies` →
  `dual_copy_files`.
- `dom_tag[int]` raises its friendly `IndexError` (it caught the wrong
  exception before).
- Dependencies: dropped unused `pytailwindcss`, `toml`, `types-toml`.
- CI installs pinned ux-channel and fails if channel tests would skip.
- Code formatted with black and ruff's safe fixes; docs snippets fixed.

## 0.2.0 — remove deprecations

- Removed deprecated modules `ux_dom.dom.ui` (Tortoise form helper),
  `ux_dom.dom.src.pythontags`, `ux_dom.dom.src.sphinxtags`, `ux_dom.alpinejs.ripple_btn`.
- Removed `serve="webassets"` alias on `XElementRuntime` and
  `PackageStaticContribution`.
- **BREAKING:** any `serve=` value other than `"package_mount"` / `"dual_copy"`
  now raises `ValueError` (before: unknown values were not rejected).
- Removed `Carousel(default=)` alias. Use `index=`.
- **BREAKING: `run_build()` lost `minify=` and `skip_tailwind=`, and
  `uxdom build` lost `--skip-tailwind`.** Both were accepted and silently
  ignored (this pipeline never compiles or minifies CSS). Passing them is now
  a `TypeError` / "No such option" error. Product CSS is `uxcompose build`.
- **BREAKING: `plugins.App.web()` removed.** It was a tombstone that only
  raised `ProductHostMoved`; it now raises `AttributeError`. The product host
  is `uxcompose create-app` / `ux_compose.build(host=)`. `App.fastapi()` still
  raises `ProductHostMoved`.
- **BREAKING:** `compose_document_parts()` lost the ignored `include_controls=`
  argument, and `cli.static_assets.sync_runtime_assets()` lost the ignored
  `vendor=` and `force=` arguments. Passing them is now a `TypeError`.
- Removed 8 unused imports in `src/`. `tests/07_resilience/test_no_unused_imports.py`
  (stdlib only) and `test_dead_surface_removed.py` keep them gone.

## 0.1.1

### Security (fail closed)

- **URL attributes use an allow-list.** In URL attributes (`href`, `src`,
  `action`, `formaction`, `xlink:href`, `hx-get`, `icon`, `lowsrc`, ...), only
  relative URLs, `http:`, `https:`, `mailto:`, `tel:` and
  `data:image/{png,jpeg,gif,webp}` pass; anything else renders as
  `about:invalid#ux-dom-unsafe-url`. The check runs on `str(value)` after HTML
  entities are decoded, ignores case and browser-ignored whitespace, and the
  checked text is what renders. Applies to every renderer, including
  unescaped attributes.
- **Behaviour change:** schemes outside the allow-list are now refused, e.g.
  `ftp:`, `sms:`, `file:`, `blob:`, `data:image/svg+xml`.
- **`srcdoc` is refused** unless the value implements `__html__`.
- **Unescaped attributes can no longer break out.** `safe_attributes` is now
  per instance (it was a shared class dict, so one `DataSet` disabled
  escaping process-wide), and opted-out values still escape `&` and `"`.
- **Attribute names are validated on every render path.** Names with
  whitespace, quotes, `>`, `/`, `=` or control characters raise
  `InvalidAttributeName` (a `ValueError`), closing attribute-name injection
  through `**user_dict` spreads.
- The unescaped-attribute opt-out is HTML-only (not XHTML).
- `//host` links count as relative; see the open-redirect note in
  `docs/security/ATTRIBUTES.md`.
- **`'` is escaped in attribute values.** `escape(quote=True)` now maps `'`
  to `&#39;` (as MarkupSafe and `html.escape` do), so a value cannot break
  out of a single-quoted attribute. Rendered output changes: `'` inside
  attribute values now renders as `&#39;`, so HTML snapshot tests that
  contain `'` in attributes need updating.

### DirectoryRouter (pure-dom, examples)

- **Fail closed on unroutable modules.** A route module that exports renderable
  classes but none matching the file stem now raises `DirectoryRouterError`.
  Before, it was dropped silently and every URL in it returned 404.
- **Fixed: an explicit `get` classmethod was overwritten** by the synthetic
  page GET (the guard checked the wrong dict level), so pages lost their
  Document shell.
- **`routes=` sub-actions work as documented:** non-verb names become
  `GET /<stem>/<name>`. A listed name with no method raises, and URL-style
  entries (`"/x/[id]"`) are rejected.
- Stem matching ignores underscores: `my_page.py` → `MyPage`.

### CLI

- **Fixed: `uxdom add route` crashed** (`add_route()` had no `methods`
  parameter). It now writes files that follow the router law: `[param]` folders,
  `route.py` verb functions for param leaves, `--methods get,post`.
- **Fixed: `uxdom add route` / `add component` imported `Component` from the
  wrong module**, so generated files failed to import.

### Examples, tests, CI

- Examples migrated to the path law (`/alpine`, not `/alpine/AlpineDemo`;
  `/htmx/partial` sub-action). Self-redirect loops on `/` removed.
- standalone_showcase HMR: `add_websocket_route` (removed in FastAPI 0.141)
  replaced with a Starlette `WebSocketRoute`. The reloader's watcher now
  starts and stops through the app lifespan (before, it never started).
- Browser tests run in CI for real: `tests/browser/package.json` pins
  Playwright 1.64.1, CI installs Chromium, and `UX_DOM_REQUIRE_BROWSER=1` turns
  a missing toolchain into a failure instead of a skip. The hardcoded
  `/workspace/node_modules` import path is gone, and stale report files are
  never read.
- Dead tests for features that moved to ux-compose (always skipped) were
  replaced by boundary assertions. Source-text assertions were replaced by
  behavior tests.
- mypy: two type errors fixed (`response/serialize.py`, `ui/page_header.py`).

### Dependencies

- **`typingx` is declared** (`>=0.6.0,<0.7`). `ux_dom.compat.valio_pep649`
  imports it directly; before, it was only installed transitively via valio.

### Earlier on main (ownership hard cut)

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
  Package-static dual-copy hatch is `serve="dual_copy"`.
- **Product routing bind:** `ux_compose.routing.DirectoryRoutes` + thin adapter.
  `DirectoryRoutes` constructed from this package fails closed.
- Historical `uxdom serve` / `create-app` notes below are **pre-cut**.
- **Docs:** teaching pages no longer cite leftover product CLI, DirectoryRouter,
  plugins.App, or fail-closed `DirectoryRoutes` on this package. Canonical
  pages under `docs/reference/` replace stub cites. Examples labeled as
  render demos, not the product routing path.

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

See [START_HERE.md](START_HERE.md) · [docs/ship/STABILITY.md](docs/ship/STABILITY.md).
