# Changelog

## Unreleased

- **Fix: ``@html_response()`` / ``@streaming_response()`` (with parentheses) work.**
  They wrapped ``None``, so calling the endpoint raised ``TypeError``. Both
  decorators now share one private factory; the bare ``@deco`` form is unchanged.
- **Refactor: web_io / slots dead code.** Removed `HtmxEvents.get_event_map` (no
  consumers), the private `set_event`/`get_events` forwards, the single-impl
  `GenericAdapter` ABC (`WebSocketClientHandler` now types its adapters as
  `WebSocketAdapter`), and `WebComponentSlot.__checks__` (inherited). The
  `_adapter` usage note and `ux_dom.scripts` docstring now match the real API and
  the package URL `/ux-dom/static/x_element.js`.
- **Fix: ``Csp`` presets honour later field edits.** ``Csp.dev()`` / ``prod()`` /
  ``report_only()`` no longer cache a ``policy``, so ``c.debug_header = True`` or
  ``dataclasses.replace(c, ...)`` reach ``to_policy()``. Preset headers are unchanged.
- **Fix: ``stamp_nonce(tags=)`` is honoured in nested trees.** ``stamp_tree`` takes
  an optional ``tags=``; ``tags=("script",)`` no longer stamps ``<style>``.
- **Fix: ``@htmx.get("name")`` routes the decorated function** (it routed the
  inner decorator, so requests got 422); same for post/put/patch/delete.
  ``HtmxControl.partial_policy`` now uses ``HtmxDetails.partial``:
  only an exact lowercase ``HX-Request: true`` (as htmx sends it) is partial, so
  ``HX-Request: false`` and history-restore requests get the full page.
- **Bug: plugin / Document errors propagate.** `App.build` no longer swallows
  `Document.mount` errors; runtime `mount` and stage hooks are called once (form
  chosen by signature) so an inner `TypeError` surfaces; a hub contribution that
  raises fails the render instead of silently dropping runtime tags; nonce
  stamping no longer hides errors, and its walk only reads ``str`` tag names and
  list/tuple ``children`` (a Component field ``name: int`` no longer breaks it).
- **Fix: Alpine `dataset_*` helpers no longer raise `KeyError` inside `DataSet`; a boolean `x-transition` merged by `Fragment` / `DataSet` renders bare or keeps the other side's classes instead of `"opacity x-transition"`.**
  `x-transition` merge rule (Fragment fan-out and DataSet `attr()` stacking): `False` removes the
  attribute (string or bare); `True` / bare contributes no classes, so it yields the other side's
  classes, or a bare `x-transition` when both are bare; two class strings are space-joined.
  A repeated `x-bind` with an identical expression is deduped; a conflicting one raises
  `ValueError` naming both expressions (`:class` still joins).
- **Security (breaking default): bare ``Csp()`` is tightened to ``Csp.prod()`` on script inline and connect-src.**
  ``Csp()``, ``CspPolicy``, ``CspMiddleware``, and ``build_csp_header`` no longer
  ship script ``'unsafe-inline'`` or bare ``ws:``/``wss:``. Apps that need inline
  scripts or websockets must opt in via ``Csp.dev()`` or explicit arguments.
  ``connect_src`` replaces the default, so ``'self'`` must be listed alongside
  any cross-origin websocket. ``Csp.dev()`` is unchanged.
- **Security: ``Csp.auto()`` defaults to prod when DEBUG is unset.** Prod drops
  script ``'unsafe-inline'`` and bare ``ws:``/``wss:`` (name hosts in overrides).
- unset DEBUG now means prod; set DEBUG=1 for dev
- **Fix: Jinja export works inside a running event loop.** `render_jinja`,
  Jinja tag calls and `JinjaElement` no longer raise `RuntimeError` from async
  handlers (the sandboxed environment is now sync). Behaviour change: an async
  iterable (e.g. an async generator) passed as a context value and iterated in
  a template now raises `TypeError`; pass a list or other sync iterable.
- **Security (BREAKING): Jinja export is sandboxed and autoescaped.**
  `render_jinja` / Jinja tag calls use `jinja2.sandbox.SandboxedEnvironment(autoescape=True)`.
  Context values are escaped, and `{{ }}` / `{% %}` in tree text or string
  attributes is shown as text instead of being run as template code (it was
  server-side template injection). Pass `raw()` for hand-written Jinja in a tree.
  Pass `markupsafe.Markup` for trusted HTML in Jinja context.
- **Security (BREAKING): string HTML is never nonce-stamped.** `stamp_tree`,
  `stamp_nonce` and `prepare_html_body` used to regex-add `nonce=` to every
  `<script>` / `<style>` in a string, including injected ones. Strings now pass
  through unchanged; build trusted scripts as `script(...)` nodes.
  Migration: a string `<script>` that relied on the CSP nonce must be built as a `script()` node instead.
- **Security: htmx/SSE/WS URLs are same-origin by default.** `hx-*` /
  `data-hx-*` / `sse-connect` / `ws-connect` refuse absolute and
  protocol-relative URLs unless wrapped in ``cross_origin(...)``.
  Protocol-relative ``//host`` is also refused on ``href``/``src``.
- **Security: htmx 1.x ``connect:`` URLs.** ``hx-sse`` / ``hx-ws`` and
  ``data-hx-sse`` / ``data-hx-ws`` (htmx 1.9.2 reads both spellings) treat
  ``connect:`` as a prefix, not a scheme. ``connect:/feed`` is kept;
  ``connect:http://evil``, ``connect:https://…``, ``connect:wss://…``,
  ``connect://host``, and ``connect:javascript:…`` are refused. ``swap:`` /
  ``send:`` names that are not URLs are kept. The prefix is parsed only on
  those four attributes, and the value is split on whitespace the way htmx
  1.9.2 does (``connect:feed swap:msg``). On ``hx-get``, ``connect:/feed`` is an
  ordinary URL and is refused. A non-leading ``connect:`` does not hide a
  foreign prefix (``https://evil.com/connect:/a``). See
  ``docs/security/ATTRIBUTES.md``.
- **Security: ``hx-sse`` / ``hx-ws`` split on JavaScript whitespace.** The
  splitter is the ECMAScript ``\s`` set, including U+FEFF, so
  ``swap:x`` + U+FEFF + ``connect:wss:evil.com`` is refused on ``hx-sse``,
  ``hx-ws``, and the ``data-hx-*`` spellings. A ``swap:`` / ``send:`` name
  must match ``[A-Za-z0-9_.-]+``; a colon or any other character refuses the
  whole value. An empty name and a bare ``connect:`` are refused.
- **Security: ``hx-sse`` / ``hx-ws`` decode HTML entities before splitting.**
  ``connect:/f&#32;connect:wss:evil.com`` is refused on those attributes and
  the ``data-hx-*`` spellings. A character reference cannot glue a same-origin
  token to a foreign ``connect:``.
- **Fix: ``uxdom lint`` / ``add`` / ``ui`` print their messages again.** Output
  goes through ``typer.echo`` (errors to stderr); the swallowing
  ``ux_dom.utils.logger`` module is removed. ``uxdom doctor`` reports a
  ``ux_channel`` that fails to import as not ok (warn) with the error. The
  unused ``uxdom ui --action`` option is removed.
- **Fix: UI kit and elements defects.** ``FloatLegend`` renders a ``<legend>``
  (it raised ``AttributeError``). ``uxdom add ui`` derives a component's kit
  dependencies from its imports, so ``status_strip`` brings ``badge``.
  ``Tabs``, ``Breadcrumb``, ``FormSection`` and ``public_form`` no longer emit a
  bare ``class`` attribute. An empty ``Chart`` accepts ``style=``.
  ``DropdownMenu`` has one ``role="menu"``, with ``role="menuitem"`` on each
  item's focusable element (``li`` is ``role="none"``). ``Tabs`` buttons have
  ``role="tab"`` and a roving ``tabindex``, plus ``aria-controls`` when ``id=``
  is given. ``Progress`` clamps ``aria-valuenow`` into ``[0, max]``.
- **Fix: ``textarea`` contents are no longer pretty-indented**, so the form value
  equals the text given. **Fix: script/link dedupe keys on (tag, rel, url)** of the
  ``script[src]`` / ``link[href]`` node itself; wrappers pass through and a
  ``preconnect``/``preload`` link no longer drops the matching stylesheet or script.
  **Fix: ``uxdom add xelement`` stubs** use ``CustomElement`` / ``WebComponent`` /
  ``AlpineComponent`` with ``tag_name`` and an ``x-tagname`` template, so they construct.
- **Infra: persisted code map.** ``scripts/codemap.py`` writes
  one shard per module under ``docs/internals/codemap/``; CI fails when a
  shard is stale (``--write-changed`` rewrites only those). See
  ``docs/internals/CODEMAP.md``.
- **Bug: ``markdown=`` string kwargs reach ``render``** again; only a callable ``markdown=`` overrides the converter (F-23).

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

See [docs/START_HERE.md](docs/START_HERE.md) · [docs/ship/STABILITY.md](docs/ship/STABILITY.md).
