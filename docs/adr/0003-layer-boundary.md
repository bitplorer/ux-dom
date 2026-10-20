# ADR 0003 — Layer Boundary: ux-dom vs ux-compose

> **Diátaxis:** ADR · **Canonical:** `docs/adr/0003-layer-boundary.md` · **Layer:** ux-dom (ownership)  
> Map: [INDEX.md](../INDEX.md).

**Status:** Accepted. Prod and port pre-flight removed from `uxdom doctor` (rule 4 met by
ux-compose [#128](https://github.com/bitplorer/ux-compose/pull/128)).  
**Amended by:** [ADR 0004](0004-no-compat-shims-pre-release.md)  
**Date:** 2026-10-20  
**Scope:** Which product features ux-dom may ship. Applies to `src/ux_dom/`, the
`pyproject.toml` extras, the `uxdom` CLI and the docs. Mirrors ux-compose
[ADR 0001](https://github.com/bitplorer/ux-compose/blob/main/docs/adr/0001-ownership.md).

---

## Context

HMR, the Tailwind compiler, scaffolding, file routing and deploy moved to ux-compose in
the hard-cut PRs. The owner restated the split on 2026-10-20, in the audit session recorded in
[#59](https://github.com/bitplorer/ux-dom/issues/59):

> "ux-compose handles HMR/hot-reload, Tailwind CSS, scaffolding, file-based routing
> (DirectoryRouter) etc. — these features migrated from ux-dom to ux-compose; ux-dom
> handles DOM-related stuff, its rendering and HTML, as well as streaming responses with
> content security"

> "ux-compose brings all parts together from the ux-* repos and acts as [the] Next.js of
> React"

The second statement describes the role of **ux-compose** only: it is the composition
layer over the specialists. It does not describe ux-dom, whose identity is not analogized
to React / Next ([AGENTS.md](../../AGENTS.md#layer-ownership-hard-cut)).

Leftovers of the migration remain in ux-dom. Evidence (audit
[#59](https://github.com/bitplorer/ux-dom/issues/59); sibling clones scanned at ux-compose
`04994da`, ux-channel `d34448c`, ux-behavior `09a9a65`, ux-motion `0adae27`):

- `ux_dom.reloader` survived until #47. `DirectoryRouter` and the routing plugin are
  removed by #49.
- `plugins/protocols.py` still declares `HmrPlugin`, `StylePlugin`, `AssetsPlugin` and
  `HostPlugin`, and `App` still exposes `use_hmr` / `use_style` / `use_host`. No code in
  this repo or in any sibling implements them.
- `pyproject.toml` ships `pytailwindcss`, `uvicorn` and `python-multipart` extras that no
  module imports (#59 row C8).
- `uxdom build --package/--archive` writes a runnable deploy bundle. Verified by a real run on
  `3a95deb`: it generates `run.sh` (`exec uvicorn app.main:app`), `requirements.txt`,
  `MANIFEST.json` and `README.RUN.txt`, copies the app's `app/` and `assets/`, and copies
  `Dockerfile`, `fly.toml`, `render.yaml`, `railway.json`, `.dockerignore` and `deploy/`
  **only if they already exist** in the app; it generates none of them. `--archive` adds a
  `.tar.gz`. The bundle served `GET /` and `/ux-dom/static/x_element.js` with 200. #59 row S4
  left its owner open.
- `uxdom doctor` checks a free port, `DEBUG` in `app/settings.py`, `.env`, and a
  `.ux_dom-scaffold.json` marker that nothing writes (#59 rows C7/C12).
- Docs cited `uxcompose serve` with an app but no mode, and a `--hmr` flag. ux-compose
  `cli/serve.py` rejects a missing mode, and `--hmr` does not exist.

## Decision

**Choice:** ux-dom owns what turns a tree into bytes, plus the browser files and headers
those bytes need. ux-compose owns composition and delivery.

| ux-dom owns | ux-compose owns |
|-------------|-----------------|
| Tag trees, `__render__` / `__async_render__`, parse | Composition root (`App`, `build(host=)`) |
| `Document` shell and `.use` (control, runtime tags, CSP stamp) | Page routes, file-based routing (`DirectoryRoutes`) |
| Streaming / HTML responses (`ux_dom.response`) | HMR, hot reload and tunnel (`uxcompose serve dev`) |
| Content security (`Csp`, safe static, attr/URL guards) | Tailwind compiler, CSS watch and minify (`ux_compose.tailwind`, `uxcompose build`) |
| `className`, Document `<link>`, package static (`/ux-dom/static/…`) | App asset layout (`WebAssets`) |
| Pure-dom CLI: `doctor` (package, Document and env checks), `lint`, `profile`, `add component\|xelement\|ui`, `build` (Document/static **verify** only) | Scaffold (`create-app`), `serve dev\|prod`, `deploy`, product `doctor`, runnable bundles |
| Optional UI kit (`ux_dom.ui`) | Product kit (`uxcompose add`) |

**Stays in ux-dom:** the verify half of `uxdom build` (structure, package-static sync,
`x_element.js`, `import:app.main:app`); `uxdom add component|xelement|ui`; the pure-dom
checks of `uxdom doctor`; `className`, Document `<link>` and package static.

**Moves to ux-compose (or is already there):** the `HmrPlugin` / `StylePlugin` /
`AssetsPlugin` / `HostPlugin` slots and `App.use_hmr|use_style|use_host`; the
`pytailwindcss`, `uvicorn` and `python-multipart` extras (`dev`, `fastapidev`);
`uxdom build --package/--archive`; the doctor's `port`, `prod:DEBUG`, `prod:.env`,
`dep:uvicorn`, `scaffold` and `product-scaffold` rows.

Rules:

1. ux-dom declares no extension point for a ux-compose feature: no protocol, hub slot or
   `App.use_*` for HMR, style compile, asset layout or host.
2. ux-dom extras contain only packages that `src/ux_dom` imports. The only extra is
   `fastapi` (`ux-dom[fastapi]` = `fastapi`). It brings starlette, which
   `ux_dom.response.starlette` imports, and `install_safe_static` imports when called.
   No other `ux_dom` module needs it.
3. `uxdom` checks and writes nothing a product scaffold owns: no port, `DEBUG`, `.env`,
   scaffold marker or deploy bundle.
4. **Remove from ux-dom only after ux-compose ships the equivalent or the owner records a
   waiver** in this ADR. Each removal lands with an absence lock in `tests/07_resilience/`
   and a `changelog.d/*.removed.md` fragment that names the replacement.

### Missing in ux-compose (blocks removal)

Checked against ux-compose `04994da`; the prod and port row re-checked at `830a6ab`:

| Capability | ux-dom today | ux-compose today | Blocks |
|------------|--------------|------------------|--------|
| `pytailwindcss` extra | None: `ux-dom[dev]` / `ux-dom[fastapidev]` removed in [#80](https://github.com/bitplorer/ux-dom/pull/80) | `tailwind.py` imports it lazily; `pyproject.toml` declares only `serve` and `dev` extras, neither with `pytailwindcss` | Nothing: waived (see below) |
| Runnable bundle | `uxdom build --package/--archive` (`dist/<name>/`, `run.sh`, `MANIFEST.json`, tar.gz) | `uxcompose deploy` writes Docker/fly/render/railway/systemd files; nothing writes a runnable dir or archive | Removing `--package/--archive` |
| Prod and port pre-flight | None: `uxdom doctor --prod/--port` and the `port:`, `prod:DEBUG`, `prod:.env` rows removed; lock `tests/07_resilience/test_doctor_product_rows_absent.py` | `uxcompose doctor --prod` ([#128](https://github.com/bitplorer/ux-compose/pull/128)) checks `secret`, `DEBUG`, `.env`, `dep:uvicorn`/`dep:fastapi` and `requirements`; `--port N` adds a `port:N` row | Nothing: shipped |

**Waivers recorded:** the owner records each waiver here ("dropped, not ported") before
the matching removal PR merges.

- `pytailwindcss` extra: waived — ux-compose compiles Tailwind via its pinned,
  SHA256-verified standalone binary
  ([ux-compose #116](https://github.com/bitplorer/ux-compose/issues/116) D3/UC5); no
  ux-compose `css` extra. Owner decision D3, 2026-10-20. UC5 (the SHA256 check) is a
  ux-compose ticket, not yet merged at ux-compose `04994da`.

**Owner decision D4 (port check):** the free-port check lives in ux-compose
`uxcompose doctor --prod --port N` and reports WARN, not FAIL. It binds the `--host` that
`serve prod` uses (default `0.0.0.0`). `uxdom doctor` has no port check.

**Why:** each concern has one home, so authors cannot pick the wrong layer and the ux-dom
install stays small. ux-compose already calls `uxdom build` "Document/static verify" (its
ADR 0001); this ADR records the same split from the ux-dom side.

## Alternatives

| Option | Verdict | Why |
|--------|---------|-----|
| Keep the empty protocols and slots "for advanced hubs" | Rejected | No implementer in any sibling repo. They tell authors HMR/style/host plug into ux-dom, which is the wrong layer. |
| Fail-closed tombstones for every removed name | Rejected. (The earlier `App.fastapi` / `ProductHostMoved` exception is withdrawn by [ADR 0004](0004-no-compat-shims-pre-release.md).) | Tombstones are API to maintain. An `ImportError` / `TypeError` plus an absence lock gives the same signal. |
| Move `uxdom build` entirely to ux-compose | Rejected | Verify checks package static and the Document import, which are ux-dom concerns. Only the deploy bundle is product. |
| Delete residue now, before ux-compose has the equivalent | Rejected | Users of the extras, the bundle and the prod doctor would lose them with no replacement. |

## Consequences

- Breaking for users of `pip install ux-dom[dev|fastapidev]`, `App.use_hmr|use_style|use_host`,
  `uxdom doctor --port/--prod` and `uxdom build --package/--archive`, once each removal lands.
- Removed: `uxdom doctor --port/--prod` (and `info`'s copies) with the `port:`,
  `prod:DEBUG` and `prod:.env` rows. `uxdom build` runs the pure-dom doctor and no longer
  prints `prod:DEBUG-note`. Product readiness is `uxcompose doctor --prod [--port N]`.
- Prerequisite ux-compose work: a bundle command, unless the owner waives it above.
  `doctor --prod` shipped in ux-compose #128. The `pytailwindcss` extra is waived.
- [internals/SYSTEM.md](../internals/SYSTEM.md) no longer lists `--package` ownership as open.
- New product-ish code proposed for ux-dom is reviewed against the table above. If
  ux-compose owns the concern, the change goes there.
