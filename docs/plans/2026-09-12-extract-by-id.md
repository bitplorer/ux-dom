# PLAN-ONLY — extract-by-id public API (owner gap C2)

> **PLAN-ONLY.** Projection, not law. Law stays
> [SYSTEM.md](../internals/SYSTEM.md). Public names stay
> [API_SURFACE.md](../reference/API_SURFACE.md). `Fragment` stays a
> tree builder in [COMPONENTS.md](../reference/COMPONENTS.md).
>
> Do not implement on this branch. Do not add `fragment.py`. Do not
> restyle `Document` / `uxdom` CLI. Do not invent a sixth product.
> Do not add a hard dep that breaks channel Soft 1 / Soft 4
> prefer-owner (ux-dom stays importable without ux-channel).
>
> **Verified 2026-09-12** vs ux-dom `main` `e8be99a` and compose#80
> maturity map **C2**.

Cite: [ux-compose#80](https://github.com/bitplorer/ux-compose/pull/80)
`docs/plans/2026-09-12-telos-maturity-map.md` row **C2**.

---

## 0. Status one-screen

| Layer | Tip | Extract-by-id |
|-------|-----|----------------|
| **ux-dom** | `e8be99a` | **absent** on `ux_dom.response.serialize.__all__` |
| **ux-compose** | `52714fc` (#79) | homemade `_fragment_for_target` KEEP (C2) |
| **ux-channel** | `d0412c6` Soft 1–4 | leftover `_guess_target_from_html` (selector guess, not extract) |

**Telos lock:** ux-dom = tree → HTML serialize (`__render__` /
`to_html_bytes`). Extract is an **owned capability of serialized HTML**
if evidenced — not a `Document.use` restyle, not a CLI verb, not a
second product.

**Owner gap (human proceed):** Library quality gate = extract-by-id
public API. Compose `_fragment_for_target` **KEEP** until this exists
and is locked. `Fragment` is a tree builder, not extract.

---

## 1. TELOS + ponytail

| Layer | Telos (owns) | Must not own |
|-------|--------------|--------------|
| **ux-dom** | Tree → HTML, Document shell, package static, `uxdom` | Product CLI, Tailwind compiler, Intent/Cap, MorphState |
| **ux-compose** | Author composition + `uxcompose` | Re-implementing serialize / extract once the owner ships it |
| **ux-channel** | Intent → Cap → Result; wire; `mount_channel` | HTML trees, Document serialize, extract-by-id |

**Ponytail** (shrink only in this order — never reverse):

1. **YAGNI** — one function. No selector engine, no CSS query, no
   `extract_by_attr`, no tree-walk twin of `getElementById`.
2. **Reuse the owner** — compose / channel **USE**
   `ux_dom.response.serialize.extract_by_id` when present.
3. **stdlib** — `re` + quote-aware scan (same contract as compose
   walker). Do **not** parse-then-re-serialize (pretty / attr order
   would change morph identity).
4. **Minimum local** — helpers stay private in `serialize.py`. No
   `fragment.py`. No new package.

**Why not tree `getElementById`:** that API already exists on live
tags (`dom1core.getElementById` / `node.get(id=)`). C2 leftover is
**post-serialize string strip** (FullShellHello `render()` returns a
full HTML *string* that *contains* `#target`). Tree query cannot
replace that walker.

**Why not `Fragment`:** `Fragment` merges children without a wrapper.
It builds trees. Extract slices serialized HTML. Different job.

---

## 2. Evidence where extract is needed

### 2.1 Compose walker (C2 — primary)

[compose#80](https://github.com/bitplorer/ux-compose/pull/80) C2:

> Extract `#id` from serialized HTML · **Owner:** ux-dom (missing on
> serialize `__all__` @ `e8be99a`) · **Compose door:** homemade
> `_fragment_for_target` (`helpers.py:121-124`, walker `:166+`) ·
> **Verdict:** KEEP until ux-dom extract. No `fragment.py`.

Live compose (`52714fc`) `src/ux_compose/helpers.py`:

| Symbol | Job |
|--------|-----|
| `_serialize_tree` | **USE** owner — `to_html_bytes` |
| `_fragment_for_target(html, target_id) -> str` | homemade outer-HTML slice for `#id` |
| `_element_end` / `_open_tag_id` / `_skip_quoted` | walker internals |
| `_render_html` / `update_with` | call the walker after serialize |

Locked contract (do not “improve”):

- Empty `html` or empty id → return `html` unchanged.
- `target_id` may be `"hello"` or `"#hello"` (`lstrip("#")`).
- First matching `id=` wins; return exact `html[start:end]` including
  the element (void / self-close / nested same-name depth).
- Skip `<!-- … -->`, `</`, `<!`, `<?`.
- Quoted attributes: `id` inside a quoted value is not a match.
- Missing id → return `html` as-is (safety net, not an error).
- Already-fragment (root id == target) is unchanged.

Compose CTO lock: `tests/feature/test_cto_fragment_law.py`
(FullShellHello `render()` is a full shell containing `#hello`;
`update_with` morph payload must be the `#hello` subtree, no brand
chrome). Deleting the walker without an owner API drops fragment-law.

### 2.2 Channel leftover (secondary — different job)

`ux_channel.protocol.encode._guess_target_from_html` (`d0412c6`):

```text
first data-channel-id="…"  →  [data-channel-id="…"]
else first id="…"          →  #…
```

This **infers a selector**. It does **not** extract a subtree.
Absorbing guess-target into extract-by-id would be channel gutting
and the wrong telos.

**Leftover teaching (Phase B, this repo only):** name the leftover.
Do not port encode.py. Do not add a hard dep on ux-channel. Soft 1
(`to_html` prefers `to_html_bytes` when present) and Soft 4
(`render/response.py` → `ux_dom.response`) stay prefer-owner / no
hard dep. Extract ships the same way: optional import from
`ux_dom.response.serialize`.

---

## 3. Proposed public API

One name, one module, one `__all__` row.

```python
# src/ux_dom/response/serialize.py
def extract_by_id(html: str, target_id: str) -> str:
    """Return the outer-HTML slice for ``#target_id``.

    Morph payload law: subtree for the id, not a document shell.
    ``target_id`` may be ``hello`` or ``#hello``. Missing / empty
    id leaves ``html`` unchanged. Already-fragment HTML is unchanged.
    """
```

| Surface | Action |
|---------|--------|
| `ux_dom.response.serialize.__all__` | **add** `"extract_by_id"` (SSoT) |
| `ux_dom.response.__all__` | **add** `"extract_by_id"` (same door as `to_html_bytes`) |
| `ux_dom.__init__` / root `__all__` | **KEEP out** — Soft 1 lock: no root fashion add |
| `Document` / `uxdom` CLI | **KEEP out** |
| `Fragment` / new `fragment.py` | **FORBIDDEN** |

Callers (compose, later):

```python
from ux_dom.response.serialize import extract_by_id, to_html_bytes

html = to_html_bytes(tree).decode("utf-8")
payload = extract_by_id(html, component.id)  # or "#hello"
```

`bytes` input is YAGNI. Compose already decodes. Trees go through
`to_html_bytes` first — extract is string-in / string-out.

---

## 4. Pattern / Clarity gate

A DO row ships only when **both** pass (compose#80 §8):

| Test | Pass | Fail |
|------|------|------|
| **Pattern** | Same leftover-teach / prefer-owner / `__all__` lock as channel Soft 1+4 and compose C1 (`to_html_bytes`) | New folder, `fragment.py`, Document method, CLI verb, root `__all__`, new product door |
| **Clarity** | Names the leftover; one concern; same-commit test lock | Encyclopedia-only, or “while we’re here” (Cap, CLI, parse-html rewrite) |

**Stop / revert if:** Isolation / leftover-teaching red · new root
`__all__` · `fragment.py` added · `mount_channel` mentioned as a cut ·
ux-channel added as a hard dep · `Fragment` class restyled as extract.

---

## 5. Soft order

| # | Status | Next |
|---|--------|------|
| Channel S1–S4 | **empty** (`d0412c6`) | none — do not relaunch |
| Compose C2 walker | **KEEP** | not a compose Soft this turn |
| **Phase A** | this PR | PLAN-ONLY; no serialize `__all__` change |
| **Soft 1 (Phase B)** | parked until plan exists | `extract_by_id` + tests-as-locks RED→GREEN |
| Soft 2 leftover teaching | same Soft 1 PR if one concern | serialize docstring + `API_SURFACE` one row |
| Compose USE owner | **after** Soft 1 lands + pin | compose PR; walker becomes leftover-teach |
| Channel guess-target | **KEEP** | different job; no gut |

No Soft 3 is evidenced. Do not merge Phase A and Soft 1.

---

## 6. Test-lock matrix (Phase B — do not run on this PR)

| L | Lock file (proposed) | What it proves |
|---|----------------------|----------------|
| L1 | `tests/01_core/test_extract_by_id.py` | `"extract_by_id" in serialize.__all__` and `response.__all__` |
| L2 | same | empty html / empty id → passthrough |
| L3 | same | `#hello` and `hello` match; exact outer-HTML slice |
| L4 | same | already-fragment unchanged |
| L5 | same | nested shell: outer brand dropped, `#hello` kept (C2 / CTO) |
| L6 | same | comments skipped; void / self-close; quoted `id`; `id=` inside quotes ignored; nested same-name depth |
| L7 | same | missing id → html unchanged |
| L8 | same | `Fragment` still tree-builder (`render_tag is False`); no `src/ux_dom/**/fragment.py` |
| L9 | `tests/07_resilience/` or L1 | `serialize.py` does not import `ux_channel` / `ux-channel` |
| L10 | L1 | not on `Document`, not in `uxdom` `--help` product verbs, not in root `ux_dom.__all__` |

RED first: import / `__all__` fail. Then GREEN: minimum walker in
`serialize.py`. No parse-then-re-render.

---

## 7. Ranked DO / KEEP / DEAD / DO NOT

### DO (Phase B — separate PR, one concern)

| Pri | Concern | Evidence | Pattern | Clarity |
|-----|---------|----------|---------|---------|
| **P0** | `extract_by_id` on `serialize.__all__` + `response.__all__` | compose#80 C2; helpers walker; serialize `__all__` today is prepare / `to_html_bytes` only | Soft 1 prefer-owner (same import door as `to_html_bytes`) | one function; leftover named |

### KEEP

- `_fragment_for_target` on compose until they pin a tip that has this API
- Channel `_guess_target_from_html` (selector leftover, not extract)
- `Fragment` as tree builder
- `getElementById` / `node.get(id=)` as **tree** query
- Soft 1/4 prefer-owner: no hard dep either direction for extract
- `mount_channel`, Cap, Isolation — untouched
- Product CLI on `uxcompose` only

### DEAD (do not invent)

- `fragment.py` / `helpers/` fashion (compose PR #67 kill)
- Extract as `Document` method or `uxdom extract`
- CSS-selector extract / `extract_by_attr`
- Parse-HTML → tree → `__render__` as the extract implementation
- Root `__all__` fashion add (channel Soft 1 lock analogue)
- Sixth product (`ux-app`, compose-host, a second kit)

### DO NOT (kill list — honor on every follow-up)

- Fashion restyle: `fragment.py`, Document restyle, CLI restyle.
- Sixth product.
- Hard dep on ux-channel / ux-compose (breaks Soft 1/4 prefer-owner).
- Cap / channel gutting (`mount_channel`, encode.py rewrite).
- Docs-first encyclopedia / INDEX rewrite beyond a `plans/` pointer.
- Merge extract into `Fragment` or `to_fragment` (channel-bridge
  string coerce — different job).
- Re-lock compose / channel internals as ux-dom tests.

---

## 8. Phase B implementer notes (not this PR)

Files:

- Modify: `src/ux_dom/response/serialize.py` — add `extract_by_id`,
  export on `__all__`. Port compose walker contract (quote-aware,
  void set, comment skip). Keep helpers private (`_element_end`,
  `_open_tag_id`, …).
- Modify: `src/ux_dom/response/__init__.py` — re-export + `__all__`.
- Create: `tests/01_core/test_extract_by_id.py` — L1–L10.
- Modify (leftover teach, same concern): `docs/reference/API_SURFACE.md`
  one row under response / serialize. Optional one sentence on
  [COMPONENTS.md](../reference/COMPONENTS.md): `Fragment` builds;
  extract lives on serialize.

Do **not** edit compose or channel in that PR.

---

## Appendix. One screen

```text
UX-DOM @ e8be99a
  telos           tree → HTML serialize     LOCKED
  serialize.__all__  to_html_bytes / prepare   GAP: extract_by_id
  Fragment        tree builder              KEEP
  getElementById  live tree query           KEEP (not C2)

C2 (compose#80)
  _fragment_for_target   homemade walker    KEEP until owner API
  channel guess-target   selector leftover  KEEP (not extract)

PHASE A   this PR     PLAN-ONLY
SOFT 1    next PR     extract_by_id + locks
COMPOSE   later       USE owner; walker leftover-teach

DO NOT
  fragment.py · sixth product · Document/CLI restyle
  Hard dep breaking Soft 1/4 · Cap/channel gutting
```
