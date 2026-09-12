# PLAN-ONLY — TELOS tip d107209 DOM / serialize / response surface

> **PLAN-ONLY.** Projection, not law. Law stays
> [SYSTEM.md](../internals/SYSTEM.md). Public names stay
> [API_SURFACE.md](../reference/API_SURFACE.md). Serialize SSoT stays
> `tree.__render__` / `__async_render__`.
>
> Phase 0–1 cartograph only. No product code. No fashion restyle.
> No public rename for cleanliness. No GitHub Actions invention.
> No sixth product. Cap / channel / `mount_channel` KEEP.
>
> **Verified 2026-09-12** vs ux-dom `origin/main` `d107209`
> (docs plan #19 on top of product `extract_by_id` `2e894cd` #20)
> and compose `e65971b` (#83 C2 Soft USE; #84 ownership map).

Cite: [ux-compose#84](https://github.com/bitplorer/ux-compose/pull/84)
`docs/plans/2026-09-12-tip-e65971b-ownership.md` (Soft queue empty;
compose prefers `extract_by_id`). Historical C2 plan:
[2026-09-12-extract-by-id.md](2026-09-12-extract-by-id.md) (#19) —
do not cite its **GAP** appendix as current.

---

## 0. Status one-screen

| Layer | Tip | Serialize / extract |
|-------|-----|---------------------|
| **ux-dom** | `d107209` (#19 docs-only) | `extract_by_id` on `serialize.__all__` + `response.__all__` @ `2e894cd` (#20) |
| **ux-compose** | `e65971b` (#83) | **USE** owner (`helpers._owner_extract_by_id` → `serialize.extract_by_id`); walker KEEP as escape |
| **ux-channel** | `d0412c6` Soft 1–4 | leftover `_guess_target_from_html` (selector guess, not extract) |

**Telos lock (Framework Lock):** ux-dom = tree → HTML serialize
(`__render__` / `__async_render__` / `to_html_bytes`). Extract is an
**owned capability of serialized HTML**. Not a `Document.use` restyle,
not a CLI verb, not a second product. Product delivery stays ux-compose.

**Soft queue after this inventory: empty.** No reuse-owner / leftover
Soft remains that is one concern, fail-closed, and not encyclopedia or
a public rename.

`2e894cd…d107209` is docs-only (#19 plan + INDEX pointer). Product
files unchanged. Compose pin **KEEP** `2e894cd` (compose#84).

---

## 1. TELOS + ponytail

| Layer | Telos (owns) | Must not own |
|-------|--------------|--------------|
| **ux-dom** | Tree → HTML, Document shell, package static, `extract_by_id`, `uxdom` | Product CLI, Tailwind compiler, Intent/Cap, MorphState |
| **ux-compose** | Author composition + `uxcompose` | Re-implementing serialize / extract once the owner ships it |
| **ux-channel** | Intent → Cap → Result; wire; `mount_channel` | HTML trees, Document serialize, extract-by-id |

**Ponytail** (shrink only in this order — never reverse):

1. **YAGNI** — do not add a second extract, a selector engine, or a
   `to_html` twin. Do not unexport unused helpers for fashion.
2. **Reuse the owner** — compose / channel **USE**
   `ux_dom.response.serialize` (`to_html_bytes`, `extract_by_id`) when
   present. Already landed.
3. **stdlib** — extract walker stays quote-aware `re` scan. Do **not**
   parse-then-re-serialize.
4. **Minimum local** — helpers stay private in `serialize.py`. No
   `fragment.py`. No new package.

**Intent Vector** (required on every DO Soft; none in this queue):

| Field | Meaning |
|-------|---------|
| **Intent** | One capability end (the telos being served) |
| **Vector** | Owner library → caller USE site (`path:line`) |
| **Concern** | One Soft; prefer reuse-owner over rename |
| **Not** | Folder move, public rename, encyclopedia, sixth product, Actions |

---

## 2. Evidence — public surface @ `d107209`

### 2.1 Serialize SSoT (locked)

Declared in `src/ux_dom/__init__.py:28-29`,
`src/ux_dom/response/__init__.py:7-14`,
[API_SURFACE.md](../reference/API_SURFACE.md):33,
[SYSTEM.md](../internals/SYSTEM.md):9-12,
[RENDER_PHASES.md](../internals/RENDER_PHASES.md):7-8:

```text
IN  → tag trees / Document
OUT → __render__ / __async_render__  (+ optional adapters)
```

`str(node)` aliases `__render__()` (`dom_tag.py:746-752`; default
`pretty=True`). Production stream path is
`__async_render__(pretty=False)` via `prepare_html_stream`
([PRETTY_STREAM.md](../internals/PRETTY_STREAM.md)).

### 2.2 `serialize.__all__` / `response.__all__`

`src/ux_dom/response/serialize.py:19-26` and
`src/ux_dom/response/__init__.py:42-53`:

| Symbol | Kind | In-repo callers | Lock |
|--------|------|-----------------|------|
| `extract_by_id` | fn | tests only (`tests/01_core/test_extract_by_id.py`); compose #83 USE | L1–L10 strong |
| `to_html_bytes` | fn | **zero** in this tree; compose `_serialize_tree` USE (C1) | **none** here |
| `prepare_html_body` | fn | `starlette.HTMLResponse.render` only | indirect (CSP tests) |
| `prepare_html_stream` | fn | `starlette.StreamingResponse` only | indirect (stream tests) |
| `is_html_renderable` | fn | `html_response` decorator only | none direct |
| `is_stream_renderable` | fn | `streaming_response` decorator only | none direct |
| `HTMLResponse` / `html_response` | adapter | tests + leftover `DirectoryRouter` + examples | construction / CSP |
| `StreamingResponse` / `streaming_response` | adapter | tests + leftover router | some smoke-only |

Not on root `ux_dom` / `Document` / `uxdom` CLI: locked for
`extract_by_id` (`test_extract_by_id.py:32-46`). Root has **no**
`__all__` (`src/ux_dom/__init__.py`) — Soft 1 fashion add still
forbidden; do not invent a root `__all__` as a Soft.

### 2.3 Compose already prefers owner (C2)

Compose `e65971b` `src/ux_compose/helpers.py`:

| Symbol | Job |
|--------|-----|
| `_serialize_tree` | **USE** `to_html_bytes` |
| `_owner_extract_by_id` | prefer `serialize.extract_by_id`, then `response.extract_by_id` |
| `_fragment_for_target` | call owner when present; homemade walker **escape** if absent |

Owner and escape share the fragment-law contract (first `#id`
outer-HTML slice; empty/missing id leaves html unchanged). Deleting
the escape drops fragment-law on older pins
(`tests/unit/test_fragment_extract_owner.py` on compose). **KEEP**
escape on compose — not an ux-dom Soft.

Channel `_guess_target_from_html` **infers a selector**. It does
**not** extract a subtree. Absorbing it is the wrong telos.

### 2.4 DOM hub (context, not a Soft)

`src/ux_dom/dom/__init__.py` is a star-re-export hub with **no**
package `__all__` (HTML/SVG/Jinja tags, parse, Component, plus
semi-internal `dom_tag` / `ext` bases). [MODULE_MAP.md](../internals/MODULE_MAP.md)
already marks those Semi. Shrinking the hub is a public rename.
**KEEP.**

---

## 3. Hunt results (clarity / maturity)

### 3.1 Unused exports

| Export | Verdict |
|--------|---------|
| `to_html_bytes` | **KEEP** — compose C1 USE; unused in-tree is not absence |
| `is_*_renderable` / `prepare_html_*` | **KEEP** — adapter internals that are public for prefer-owner; no rename |
| `extract_by_id` | **KEEP** — compose #83 USE; in-repo tests-only is the owner shape |

Unused ≠ unexport. No public rename for cleanliness.

### 3.2 Dual doors (same job, two names)

| Job | Door A | Door B | Verdict |
|-----|--------|--------|---------|
| Sync serialize | `tree.__render__` | `to_html_bytes` (CSP + bytes) | **KEEP** — dunder SSoT; bytes helper is the compose door |
| Stream serialize | `__async_render__(pretty=False)` | `prepare_html_stream` / `StreamingResponse` | **KEEP** — adapter calls SSoT |
| Import path | `ux_dom.response.serialize` | `ux_dom.response` re-export | **KEEP** — same as `to_html_bytes` door |
| HTTP HTML | `ux_dom.response.starlette.HTMLResponse` | `from ux_dom.response import HTMLResponse` | **KEEP** — re-export |
| HTTP HTML (ecosystem) | FastAPI `HTMLResponse` (app shell) | ux-dom `HTMLResponse` (tree + CSP) | **KEEP** — different jobs |
| Endpoint wrap | `@html_response` | `HTMLResponsePlugin.wrap` | **KEEP** leftover; hub never registers plugins |
| `#id` | live `node.get(id=)` / `getElementById` | post-serialize `extract_by_id` | **KEEP** — tree vs string |
| “fragment” name | `Fragment` (tree builder) | `to_fragment` (channel coerce) / `extract_by_id` | **KEEP** — three jobs; leftover-taught |

Pretty convention: `to_html_bytes` / `prepare_html_body` call
`__render__()` at default **`pretty=True`**. Stream path is
`pretty=False`. Docs claim compact for **production streaming**, not
for `to_html_bytes`. Changing bytes to compact would shift compose
C1 HTML (whitespace / morph identity). **KEEP** — not a Soft.

### 3.3 Weak locks

| Claim | Lock | Verdict |
|-------|------|---------|
| `extract_by_id` contract | `test_extract_by_id.py` L1–L10 | **strong** |
| `to_html_bytes` on `__all__` | none in this repo | **weak** — compose depends; lock when a product Soft touches serialize, not a tests-only Soft |
| `StreamingResponse` coerce | several `assertIsNotNone` | **weak** — leftover DirectoryRouter path; new test *layer* fails Pattern |
| `API_SURFACE` vs `serialize.__all__` | docs list 2 of 6 helpers | **incomplete map** — encyclopedia-only if “fixed” alone |
| `ux_dom.dom` export set | no hub `__all__` assertion | **KEEP** — no public shrink |

Pattern gate: “new test *layer*” without a leftover / prefer-owner
gap is a fail. Tests-only Softs are out.

### 3.4 Claimed-not-real

| Source | Claim | Now | Class |
|--------|-------|-----|-------|
| [API_SURFACE.md](../reference/API_SURFACE.md):40 + `serialize.py:7-8` | Compose `_fragment_for_target` **KEEP until callers USE** | Compose #83 **USE** owner; walker is **escape** | **Stale leftover-teach** — not a denial that the API exists |
| [2026-09-12-extract-by-id.md](2026-09-12-extract-by-id.md):25, :281 | `GAP: extract_by_id` / absent on `__all__` | Shipped #20 | **Historical plan** — projection, not current law |
| `src/ux_dom/dom/__init__.py:14` | See `docs/guides/API_SURFACE.md` | That path is a Moved stub → reference | **Stale pointer** (stub exists and redirects) |
| [FEATURES.md](../reference/FEATURES.md):34 / [COMPONENTS.md](../reference/COMPONENTS.md):95-97 | `extract_by_id` on serialize; not `Fragment` | True | OK |
| [SYSTEM.md](../internals/SYSTEM.md) | Dunder SSoT; WebAssets fail-closed | True | OK |

No **named lie** of a public symbol (nothing claims an API that is
absent, or denies one that shipped). Stale KEEP-until-USE is
leftover-teach debt. Fixing it alone is encyclopedia-only (Clarity
fail). Prefer plan-only — do not edit `API_SURFACE` / `serialize.py`
on this PR.

### 3.5 Dead paths

| Path | Class |
|------|-------|
| `plugins.response.HTMLResponsePlugin` / `StreamingResponsePlugin` | Orphan wrap of the same decorators; tests instantiate; hub never registers | **KEEP** leftover |
| `html_response` via leftover `DirectoryRouter` | Product routes are ux-compose; fail-closed / leftover | **KEEP** |
| `demosite/` | Retired; product demos live in ux-compose | **KEEP** (already taught) |
| Product CLI / `WebAssets` / `DirectoryRoutes` on this package | Fail-closed; locked | Intentional dead ends |

---

## 4. Pattern / Clarity gate

A DO row ships only when **both** pass:

| Test | Pass | Fail |
|------|------|------|
| **Pattern** | Same leftover-teach / prefer-owner / `__all__` lock as channel Soft 1+4 and compose C1/C2 | New folder, public rename, Document method, CLI verb, root `__all__`, new product door, new test *layer*, GitHub Actions |
| **Clarity** | Names the leftover; one concern; same-commit test lock | Encyclopedia-only, or “while we’re here” (Cap, CLI, pretty rewrite, hub `__all__`) |

**Stop / revert if:** Isolation / leftover-teaching red · new root
`__all__` · `fragment.py` added · `mount_channel` mentioned as a cut ·
ux-channel added as a hard dep · `Fragment` restyled as extract ·
public rename for cleanliness.

---

## 5. Soft order

| # | Status | Next |
|---|--------|------|
| Channel S1–S4 | **empty** (`d0412c6`) | none — do not relaunch |
| ux-dom extract Soft 1 | **shipped** `#20` @ `2e894cd` | none |
| Compose C2 USE | **shipped** `#83` @ `e65971b` | walker escape **KEEP** |
| Compose ownership map | **shipped** `#84` | Soft queue empty |
| **This PR (Phase 0–1)** | PLAN-ONLY | no serialize `__all__` change |
| **Open Softs** | **empty** | stop |

No Soft 1 is evidenced on this surface. Do not merge leftover-teach
of API_SURFACE into a product cut that does not exist.

---

## 6. Ranked DO / KEEP / DEAD / DO NOT

### DO (Soft queue)

**Empty.**

Rejected candidates (why they fail the gate):

| Candidate | Pattern | Clarity |
|-----------|---------|---------|
| Leftover-teach API_SURFACE “KEEP until USE” → “callers USE; walker is escape” | leftover-teach would pass | **Fail** — encyclopedia-only; no product concern; cannot lock compose internals here |
| Add `to_html_bytes` contract tests | **Fail** — new test layer, no leftover | cleanliness |
| Unexport `is_*_renderable` / shrink `serialize.__all__` | **Fail** — public rename | cleanliness |
| Add `ux_dom.dom.__all__` / shrink star hub | **Fail** — public shrink | fashion |
| Collapse `response` vs `response.starlette` | **Fail** — public rename | fashion |
| `prepare_html_body` → `pretty=False` | **Fail** — behavior change, not leftover-teach | morph / pretty identity |
| Delete `plugins.response` | **Fail** — fashion restyle | leftover DirectoryRouter still calls decorators |
| Pin compose to `d107209` | n/a (compose repo) | compose#84 rejected — docs-only |
| GitHub Actions / CI workflow | **Fail** — invention | forbidden this pass |
| Absorb channel guess-target | **Fail** — wrong telos | selector leftover, not extract |
| Merge `to_fragment` / `Fragment` / extract | **Fail** — three jobs | kill list |

### KEEP

- Dunder serialize SSoT; `to_html_bytes` as compose C1 door
- `extract_by_id` on `serialize.__all__` + `response.__all__`; not root
- Compose walker **escape** (compose tree); channel guess-target
- `Fragment` as tree builder; `get(id=)` / `getElementById` as tree query
- `to_fragment` as channel-bridge coerce (different job)
- Dual import `response` / `response.starlette`; FastAPI vs ux-dom HTMLResponse
- `plugins.response` orphan wrap; leftover `DirectoryRouter` decorators
- Star `ux_dom.dom` hub without package `__all__`
- `pretty=True` default on `__render__` / `to_html_bytes`; compact on stream
- Soft 1/4 prefer-owner: no hard dep on ux-channel
- `mount_channel`, Cap, Isolation — untouched
- Product CLI on `uxcompose` only
- Historical plan #19 as projection (GAP appendix is pre-ship)
- Stale API_SURFACE KEEP-until-USE leftover-teach until a *product*
  Soft exists (do not encyclopedia it alone)
- Compose pin `2e894cd` (this tip is docs-only)

### DEAD (do not invent)

- `fragment.py` / `helpers/` fashion
- Extract as `Document` method or `uxdom extract`
- CSS-selector extract / `extract_by_attr`
- Parse-HTML → tree → `__render__` as extract
- Root `__all__` fashion add
- Sixth product (`ux-app`, compose-host, a second kit)
- GitHub Actions / workflow files as a “lock”
- A second serialize SSoT

### DO NOT (kill list — honor on every follow-up)

- Fashion restyle: `fragment.py`, Document restyle, CLI restyle,
  `dom.__all__` shrink, adapter import collapse.
- Public rename for cleanliness.
- Sixth product.
- Hard dep on ux-channel / ux-compose (breaks Soft 1/4 prefer-owner).
- Cap / channel gutting (`mount_channel`, encode.py rewrite).
- Docs-first encyclopedia / INDEX rewrite beyond a `plans/` pointer.
- Merge extract into `Fragment` or `to_fragment`.
- Re-lock compose / channel internals as ux-dom tests.
- Invent GitHub Actions.
- Relaunch channel Soft 1–4 or compose C2.

---

## 7. Named-lie check (product code gate)

This pass may edit product code only for a **named lie**. None found:

- `extract_by_id` exists where FEATURES / COMPONENTS / `#20` say it does.
- `to_html_bytes` exists where API_SURFACE and compose C1 say it does.
- SYSTEM / RENDER_PHASES dunder SSoT matches `dom_tag.__render__`.
- Fail-closed WebAssets / DirectoryRoutes match tests.

Stale KEEP-until-USE is leftover-teach, not a missing/denied API.
Stub pointer `docs/guides/API_SURFACE.md` resolves. **No product
edit on this branch.**

---

## Appendix. One screen

```text
UX-DOM @ d107209  (product @ 2e894cd #20)
  telos              tree → HTML serialize     LOCKED
  serialize.__all__  extract_by_id + to_html_bytes + prepare/is_*
  extract            SHIPPED; compose #83 USE
  Fragment           tree builder              KEEP
  getElementById     live tree query           KEEP
  to_html_bytes      compose C1 door           KEEP (untested here)
  adapters           optional Starlette        KEEP
  plugins.response   orphan wrap               KEEP leftover

COMPOSE @ e65971b
  _fragment_for_target   prefer owner + escape KEEP
  channel guess-target   selector leftover     KEEP

SOFT QUEUE                                 EMPTY
FRAMEWORK LOCK                             HELD

DO NOT
  public rename · GitHub Actions · fragment.py
  sixth product · pretty rewrite · encyclopedia Soft
  Cap/channel gutting · hard dep breaking Soft 1/4
```
