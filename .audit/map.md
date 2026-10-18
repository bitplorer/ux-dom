# ux-dom Stage 1 map

- **Repo:** bitplorer/ux-dom. **SHA:** `19af869ecbb108f3cf779111838e3359b33a8131` (main, 2026-10-16). **VERSION:** 0.2.0. Not on PyPI (pypi.org/pypi/ux-dom → 404).
- **Release refs:** origin has **no git tags**. The release commits are used as anchors: 0.1.0 = `b6aed63`, 0.1.1 = `3b85987`. 0.2.0 has no release commit; it is HEAD.
- **Machine-readable:** `map.json` (modules, imports, cycles, importers, consumers, greps, pins, and API snapshot pointers), `consumers.json`, `pins.json`, `api-{0.1.0,0.1.1,HEAD}.json`, `apidiff-*.json`, `examples-run.json`.

## Counts
| Item | Value |
|---|---|
| src modules / LOC | 142 / 23,337 |
| Public modules / names at HEAD (runtime walk) | 129 / 1,227 |
| Top-level `ux_dom` names | 25 (no `__all__`; 2 star imports at `src/ux_dom/__init__.py:57-58`) |
| CLI `uxdom` | add, build, dashboard, doctor, info, lint, profile, ui (`src/ux_dom/cli/cli.py:30-219`) |
| Test files / tests | 94 / 922 (920 pass, 2 error on main, browser suite included) |
| Modules with no test importer | 78 / 142 |
| Import cycles (module-level SCC) | 2: `dom_tag↔dom_util`; a 13-module cycle `ux_dom↔dom↔htmldocument↔htmlelement↔plugins.control(.htmx)↔runtime↔settings(.document)↔slots(4)` |
| Orphan candidates (no src, example or external importer) | 12: alpinejs, assets, cli.envfile, compat, debug_gallery, examples.links, examples.toggle, plugins.response, routing (pkg), settings.paths, utils, utils.functional |
| Greps in src | TODO-class 4; compat/legacy/shim 50; eval/exec/pickle/innerHTML 1; `except Exception:` lines 62 |

## Modules (package level)
| Package | Mods | LOC | External consumers |
|---|---|---|---|
| `dom.src` (tag engine, parser, component, concurrency, jinja) | 16 | 6,921 | ux-compose, ux-channel, ux-motion (**private path**) |
| `ui` (shadcn-style kit) | 39 | 2,881 | harbor only |
| `plugins` (hub, csp, safe_static, runtime, control) | 18 | 2,785 | ux-compose, ux-motion, harbor |
| `cli` | 10 | 2,036 | none |
| `dom` (public tags, htmlelement, icons) | 6 | 1,773 | all four siblings + harbor |
| `elements` (valio form fields) | 8 | 1,588 | none |
| `routing` (DirectoryRouter) | 3 | 829 | harbor only |
| `web_io`, `settings`, `utils`, `response`, `reloader`, `alpinejs`, `compat`, `profiling`, `slots`, `assets`, `htmx`, `examples`, `runtime`, misc | 47 | 4,524 | `response`: ux-compose, ux-channel; `runtime`: ux-compose |

## Consumers (`consumers.json`; every imported name resolved against HEAD)
- **ux-compose** (pins `0440ccb`, 6 behind main): 61 names, all resolve. Private imports: `dom.src.component.Component` (`ux_compose/component.py:29`), `dom.src.dom_tag.dom_tag` (:30), `dom.src.utils.dom_util.raw` (`dom.py:76`, `routing/core.py:217`).
- **ux-channel** (no pin, peer): 18 names, all resolve. Private: `dom.src.utils.escape` (`render/html_safe.py:61`).
- **ux-motion** (undeclared): 10 names, all resolve. Private: `dom.src.component.Component` (`ux_motion/_dom.py:21`).
- **ux-behavior**: 0 imports in src (tests/docs only). **ux-valio, cek-python, cek-runtime, cek-framework:** none. cek-host/cek-surface: not on GitHub (PyPI only, not ux-dom consumers per quality review).
- **harbor** (unpinned `git+…ux-dom.git`): 66 names, **4 broken at HEAD**: `ux_dom.WebAssets`, `ux_dom.plugins.hmr.HotReload`, `ux_dom.plugins.style.TailwindStyle`, `ux_dom.settings.commands.TailwindCommand`.

## 1a Unpushed work (read-only scan, `GIT_OPTIONAL_LOCKS=0`)
- **ux-dom `fix/high-n1-n3`** @ `6953b48` (2026-10-18 07:35 IST): **16 commits on no remote**, in `/workspace/review2-ux-dom` and worktree `/workspace/review4-n1n3`. It holds the N1–N3 security fixes (review8 PASS), stacked on `cleanup/deep-2026-10-17` (`064777a`, which is on origin, 35 ahead of main).
- ux-dom dirty trees (superseded, content already on main): `deprecation_sweep/ux-dom` (25 staged, 0.2.0 deprecation work = PR #25), `quality_review/fix/ux-dom` (7: escape-quote, minify, typingx = PRs #27/#28), `r2fix/ux-dom` (CHANGELOG, 1 file).
- Siblings: ux-compose `review2-deps` `chore/bump-ux-dom-pin` (1 commit, pins ux-dom `2e67101`, which is **not on ux-dom main**), `uxc-pr` (5), `rv_p1 rv-combo` (1); ux-valio (1); cek-python (2), cek-runtime (1+1); ux-channel-scan (1). Large dirty sweep trees: ux-compose ×5 (204–248 files), ux-channel ×3, ux-behavior (18).

## 1b Pin map (`pins.json`)
| Consumer → dep | Pin | Head | Behind |
|---|---|---|---|
| ux-compose → ux-dom | `0440ccb` | `19af869` | 6 |
| ux-compose → ux-channel | `f1a93fc` | `83a580a` | **84** |
| ux-compose → ux-behavior | `2ae5c3d` | `2242a7d` | 6 |
| ux-compose → ux-motion | `bbe7d73` | `25d2bf9` | 10 |
| ux-channel → ux-dom | `"ux-dom"` (name only, peer, unresolvable from PyPI) | — | — |
| harbor → ux-dom | unpinned git main | — | broken |
| ux-motion, ux-behavior → ux-dom | **undeclared** | — | — |
| ux-dom → valio | `>=0.1.0b6,<0.2` (lock 0.1.0b6 = PyPI latest; successor `ux-valio` 0.2.0 unused) | — | — |
| Python floor | ux-dom `>=3.14,<3.15`; ux-channel `>=3.14,<4`; others `>=3.14`; valio `^3.10`; harbor `>=3.10` | | |

## 1c API snapshot
- HEAD: 129 modules, 1,227 names, 8 CLI commands. 0.1.1: 132 / 1,530 / 8. 0.1.0: 121 / 1,515 / 13.
- 0.1.0 → 0.1.1 (a **patch** bump): 10 modules removed (cli.deploy, cli.scaffold(_check), create.*, plugins.hmr, plugins.host(.fastapi), settings.commands), 48 names removed (WebAssets, TailwindCommand, Dir*, …), and 6 CLI verbs removed (create-app, deploy, dev, examples, plugins, templates).
- 0.1.1 → HEAD (0.2.0 minor): 3 modules removed (alpinejs.ripple_btn, dom.src.pythontags, sphinxtags). Signature narrowings: `run_build` (−minify, −skip_tailwind), `build --skip-tailwind`, `compose_document_parts` (−include_controls), `sync_runtime_assets` (−force, −vendor), `Tags.safe_attributes` (class attribute → per-instance), `App.web` removed. All listed in CHANGELOG 0.2.0.

## 1e Map check at this SHA
PASS: all 142 mapped paths exist, every runtime-exported module is mapped, cycles = 2 (baseline). The script is `.audit/tools/mapcheck.py`; see below.

## Changes since map (stage 5)

- PR fix/jinja-sandbox-nonce-trees: `dom.src.jinjatags.render_jinja` now renders through a module-level `SandboxedEnvironment(autoescape=True)` and hides `{`/`}` in tree text + string attrs (private-use placeholders → `&#123;`/`&#125;`). `dom_text` gains `.escaped`. `plugins.csp._inject_nonce_html` removed; `stamp_tree`/`stamp_nonce`/`prepare_html_body` no longer touch `str`. No module added/removed.

- PR fix/sanitize-html-parse: `dom.src.html_string` always sanitises string→markup (unsafe tags/attrs); braced-data raw hole closed. No module added/removed.
- PR fix/entity-roundtrip: bare-& escape + Entity/Char emit.
- PR fix/htmx-same-origin-urls: SAME_ORIGIN_URL_ATTRIBUTES + cross_origin; // refused on href/src.
- PR fix/csp-auto-prod-defaults: auto unset→prod; prod no unsafe-inline/ws.
- PR fix/mount-fail-loud: Document.mount raises if static install is 0.
- PR fix/build-parallel-context: sequential under with-tag.
- PR fix/build-parallel-context: sequential under with-tag so children attach (F-08).
- PR fix/valio-patch-fail-closed: ensure_valio_pep649 marks applied only on success; raises on failure (F-09).
