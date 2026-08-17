# Design Decisions — Channel-Native Design System for ux-app

**Status:** Authoritative decision record  
**Date:** 2026-08-17  
**Scope:** Every architectural, API, naming, visual, and process choice made while building this system, with the reason it was chosen and the alternatives rejected.

**Rule for readers:** If a decision is not listed here, it was either not intentional or must be treated as unset. Do not invent implicit intent.

---

## 0. How to use this document

- **Redesigning:** Start here. Change a decision only after recording a new ADR-style entry that supersedes the old one.
- **Implementing:** If code and this document disagree, fix the code or update this document in the same change — never leave them divergent.
- **Reviewing:** Council seats (Law, Channel, Document, Domain, Design, Author, Adversary) use this as the checklist of locked choices.

---

## 1. Product identity and north star

### D1.1 — What this is
**Choice:** A **channel-native design system layer** for Host-authored apps on ux-app / ux-dom — not a website, not a second kernel, not a React/TypeScript library, not a fork of ux-surface / uxkit / cek-surface.

**Why:** ux-app is already defined as an L7 author layer on ux-dom + ux-channel. A design system that forked those cores would violate isolation law and create two sources of truth. Product engineers need drop-in UI vocabulary (shadcn-like) that still obeys Cap / Op / stamp / two-clock rules.

**Rejected:** Building a standalone “ux-design-system” package that reimplements Document or Channel.

### D1.2 — Success metric
**Choice:** A staff engineer can build a complex dashboard + multi-step sealed flow with near-zero custom client JS, doctor/isolation/golden paths green, and UI that reads as intentional operational craft (not prototype).

**Why:** Matches FAANG-internal-tools bar stated in the master contract and the user’s rejection of “newcomer / unprofessional” Host UI.

### D1.3 — Minimal client-side surface (hard requirement)
**Choice:** Anything that *can* be pushed to the server *must* be pushed. Product authority **and** interactive chrome (dialog open, tab selected, sheet, command, carousel index) prefer Channel over client runtimes.

**Why:** User explicitly required Channel-based solutions for local chrome, not only for product state. Historical Alpine-for-open patterns reintroduced client authority and visual inconsistency.

**Rejected:** “Local chrome = Alpine is fine by default.”

---

## 2. Ownership and package boundaries

### D2.1 — Split ownership
| Concern | Owner | Why |
|---------|--------|-----|
| Markup, tokens, pure components | **ux-dom** | Document / Tailwind / create-app already live there; moving markup to ux-app would create a second design system |
| Author macros for chrome (open/close/select) | **ux-app** | Expands to `Op`; author layer owns Actions → list[Op] |
| Cap mint, Peer apply, stamp | **Channel / CEK via adapter/** only | Isolation law: only `src/ux_app/adapter/**` may import `ux_channel` / `cek_*` |

**Rejected:** Putting tokens inside ux-app; putting Channel imports in overlay macros; a third package that owns both markup and Ops.

### D2.2 — ux_app.ui remains a re-export
**Choice:** `ux_app.ui` continues to re-export `ux_dom.ui` when ux-dom is installed; ownership of markup does not move.

**Why:** Existing COMPONENTS.md and cold-import story already define this. Changing it would break day-1 DX and isolation docs.

### D2.3 — Artifact package vs live repos
**Choice:** Work delivered first as a complete package under `design_system/`, then promoted by copy into live ux-dom / ux-app trees.

**Why:** Sandbox had no durable `/workspace/host_ui` and incomplete clones; promoting without a coherent package would scatter half-finished files. Explicit promote path is documented in IMPLEMENTATION_STATUS.

---

## 3. Channel authority and chrome model

### D3.1 — Chrome preference order (strict)
1. **Channel** — session cell + Action + morph (or pure CSS `:target` / `<details>`)
2. **CSS-only / declarative** — no JS
3. **Stock XElement / peer perception** — pure perception, zero product meaning
4. **Declared Alpine** — last resort; must be `declare_runtime` + `require_composite`

**Why:** User required Channel for chrome. Preference order prevents silent regression to Alpine defaults while still allowing pure-perception exceptions.

**Rejected:** Alpine as default for Dialog/Tabs (current live ux-dom Dialog/Tabs use Alpine; elevated versions do not).

### D3.2 — One overlay cell
**Choice:** Default morph target for open/close is a single region id `"overlay"`. Kind + payload live in session keys; render path dispatches on kind.

**Why:** Host desk law already used one overlay cell (data-open). Multiple simultaneous modals complicate focus, escape handling, and morph identity. Multi-overlay later = new adapter or explicit target override, not product Actions inventing cells.

### D3.3 — Session key scheme (adapter-only)
**Choice:**
```text
ui.overlay.open      bool
ui.overlay.kind      str   # "dialog" | "sheet" | "command" | "confirm" | …
ui.overlay.payload   dict
ui.select.<region>   str   # active tab / page / accordion key
```

**Why:** Single, predictable namespace under `ui.*`. Product Actions never hard-code these strings — only adapters do. Renaming keys = one adapter change.

**Rejected:** Per-dialog keys like `ui.dialog.open` / `ui.dialog.lot_id` as the *author-facing* contract (allowed only inside payload, not as the public macro API).

### D3.4 — Open/close expands only to S pairs by default
**Choice:** `open_overlay` / `close_overlay` / `select_region` expand to `kv.set` / `kv.delete` / `ui.dom.morph` only.

**Why:** S pairs are always understood; no domain stamp required for basic chrome. Matches `notify` / `go` / `update` design. Domain-stamped pairs stay for rich effects (`ui.notice.push` after `app.use("effects")`).

---

## 4. Interface-first composition (ports / adapters)

### D4.1 — Ports exist
**Choice:** `OverlayPort`, `SelectPort`, `MorphPort`, `TokenPort`, `ConfirmPort` as `typing.Protocol` contracts.

**Why:** User required that if something breaks, handling stays at the interface level, not across the entire surface. Product Actions and macros depend on ports; concrete kv keys and morph strategy live in adapters.

### D4.2 — Default adapters are Channel-backed
**Choice:** `ChannelOverlay`, `ChannelSelect`, `ChannelConfirm`, `SMorph`, `TableTokens`.

**Why:** Matches Channel-first law. `ChannelConfirm` composes `OverlayPort` rather than duplicating kv logic.

### D4.3 — Module-level `bind_*` for injection
**Choice:** `bind_overlay` / `bind_select` / `bind_confirm` mutate module defaults.

**Why:** Sufficient for unit tests and single-process Host. Simpler than App-scoped DI for Phase 1–7.

**Deferred (explicit):** App-scoped port injection for multi-tenant or multi-App processes. Not required for current Host model; document if introduced later.

### D4.4 — Macros are a thin façade
**Choice:** `ux_app.overlay` only delegates to bound ports; no key strings in the façade body.

**Why:** Ensures redesign of storage never requires editing every product Action.

---

## 5. Elevation rule (batching Ops)

### D5.1 — Rule statement
**Choice:** If authors batch Ops and the batch is a **recurring design-system pattern**, promote it to a **dedicated named interface** (port method + macro). Only true one-off product logic stays as explicit `Op` lists.

**Why:** User required that lower-level Ops appear only when truly required, and that design-level batches become dedicated interfaces. Prevents copy-paste of kv+morph sequences across product Actions.

### D5.2 — Elevated macros shipped
| Macro | Pattern elevated | Expands to |
|-------|------------------|------------|
| `open_overlay` | Open overlay + kind + payload + morph | kv×3 + morph |
| `close_overlay` | Close + clear kind/payload + morph | kv + delete×2 + morph |
| `select_region` | Select tab/page + morph | kv + morph |
| `confirm` | Confirm dialog open with structured payload | via `open_overlay("confirm", …)` |
| `form_result` | Form morph + optional notice | morph + optional log + notices morph |

**Why each:** Each appeared (or would appear) as a repeated Op batch in Host/desk Actions. Elevating once keeps Actions intent-level.

### D5.3 — When explicit `Op` is still correct
**Choice:** Custom morph payload shapes; domain-stamped pairs; truly unique product logic not shared across screens.

**Why:** Macros must not become a second protocol that hides all Ops. Advanced authors retain `Op`.

---

## 6. Naming

### D6.1 — Module is `overlay`, not `chrome`
**Choice:** Façade module named `ux_app.overlay`.

**Why:** `isolation.BANNED_PUBLIC_NAMES` includes `chrome`. Exporting or centering the public story on the word `chrome` fails Adversary/Author gates. Macros use verbs: `open_overlay`, `close_overlay`, `select_region`, `confirm`.

**Rejected:** Public package or `__all__` entry named `chrome`.

### D6.2 — Document title may still say “chrome”
**Choice:** Internal docs may use “chrome” descriptively (interactive open/selected UI chrome).

**Why:** Banned list targets public API identifiers, not English explanation. Still avoid putting `chrome` in `__all__`.

### D6.3 — Frozen and banned vocabularies (inherited from ux-app)
**Frozen CEK words:** Cap, Intent, Host, Peer, Op, Result, stamp, domain, driver, …  
**Author-facing:** App, Component, Action, Event, State, update, notify, go, follow_up, preview, use, domain.  
**Banned from public API:** chrome, arm, reply, Effect, Surface (as product type), command (as Action substitute), VStack as product, …

**Why:** Live BUILD_PRODUCT_LIBRARY / isolation.py law. This design system does not invent synonyms.

### D6.4 — Overlay kinds are plain strings
**Choice:** `kind="dialog" | "sheet" | "command" | "confirm" | …` as strings, not an enum type in the public macro.

**Why:** Open for product-specific kinds without core releases. Render path switches on kind. Validation of unknown kinds is a Host/render concern, not a hard macro failure (except empty kind).

---

## 7. Visual / token system

### D7.1 — Token tables in Python, values are Tailwind class strings
**Choice:** `surface`, `ink`, `type_scale`, `target`, `density`, `overlay`, `color` maps in `tokens.py`; components call them via `cn(...)`.

**Why:** Matches existing ux-dom UI kit (cn/variants/radius/focus_ring). No CSS-in-JS, no second theme runtime. Ownable copy stays pure Python + Tailwind.

### D7.2 — Surface levels L0–L3
**Choice:**
- L0 page / site-frame  
- L1 card / panel  
- L2 elevated / modal body  
- L3 popover / command  

Plus `_light` variants for light products.

**Why:** Material-inspired hierarchy; Host desks were flat single-level brown. Explicit levels let Host delete local surface hacks.

### D7.3 — Dark operational defaults first
**Choice:** Default surface/ink tables are dark stone/emerald operational palette.

**Why:** Existing Host screenshots and desk product are dark. Light variants exist for products that need them; dark is not an afterthought.

### D7.4 — Primary target size = min-h-11 (44px)
**Choice:** `target["md"] = "min-h-11 h-11 …"`; Button/Input default to md.

**Why:** Operational / touch accessibility bar from the Host council work. Sub-44 primary actions were a recorded defect.

### D7.5 — Stone + emerald, not slate-only
**Choice:** Elevated kit uses stone for paper/ink and emerald for accent/success; destructive remains red.

**Why:** Differentiate operational craft from default shadcn slate samples; Host aesthetic was olive/stone-adjacent. Still pure Tailwind utilities.

### D7.6 — No second design system
**Choice:** Elevate existing ux-dom UI kit in place; do not introduce a parallel component namespace or CSS framework.

**Why:** NORTH_STAR kill trigger; Document seat veto.

---

## 8. Component design patterns

### D8.1 — Pure server HTML components
**Choice:** Components are ux-dom `Component` subclasses rendering server HTML. Channel is optional at render time.

**Why:** Core stack law. Progressive enhancement: markup works without Channel; live_button degrades to data-channel-action stubs when Channel absent.

### D8.2 — Dialog / Tabs: Channel-first implementations
**Choice:** New Dialog takes `open: bool` and renders open or closed markup from the server. Tabs takes `active: str` and renders only the active panel + tab list. No `x-data` / `x-show` by default.

**Why:** D3.1. Live Alpine Dialog/Tabs remain historical in upstream until replaced; elevated package versions are the design-system path.

**Rejected:** Keeping Alpine as the default path for these composites in the elevated kit.

### D8.3 — className always wins
**Choice:** Every component accepts `className=` merged last via `cn`.

**Why:** Ownable / overrideable like shadcn; required for product branding without forking components.

### D8.4 — Inventory prioritization
**Shipped in elevated package:** tokens, Button, Input, Card, Badge, Label, Separator, Textarea, Skeleton, Checkbox, Switch, Select, Alert, Table (+ Empty), Dialog, Tabs, EmptyState, PageHeader.

**Deferred (explicit):** Slider polish, Carousel, Chart, DatePicker, Sheet as separate component file, Popover, DropdownMenu, Command, Breadcrumb, Pagination, Sidebar, DataTableView, SearchCombobox as full components.

**Why defer:** Phase plan ordered foundation → forms → overlays → patterns. Overlay *behavior* is covered by macros + Dialog; Sheet/Command can reuse `open_overlay(kind=...)` + render dispatch without separate files in the first complete package. Full shadcn inventory remains the roadmap, not an incomplete claim of “done for every name.”

### D8.5 — Patterns vs primitives
**Choice:** EmptyState and PageHeader are patterns (composed layout), not token-level primitives.

**Why:** Three-layer hierarchy (foundation → design system → feature/pattern). Patterns may compose primitives and accept action slots.

---

## 9. API shape for authors

### D9.1 — Verb macros, not Op constructors, for chrome
**Choice:** `open_overlay(...)`, not `Op.kv_set("ui.overlay.open", True)` in product code.

**Why:** Matches `notify` / `go` / `update`. Intent-level Actions.

### D9.2 — `confirm` is not a separate session protocol
**Choice:** `confirm(...)` is sugar over `open_overlay("confirm", ...)` with a structured payload (`title`, `body`, `confirm_action`, labels).

**Why:** One overlay cell, one open path. Confirm is a kind + payload, not a second cell type.

### D9.3 — `form_result` includes optional notice
**Choice:** Always morphs form target; if `message` non-empty, also log.append + notices morph (S-only, same as `notify`).

**Why:** Common form submit outcome batch. Does not emit undeclared `ui.toast`.

### D9.4 — Caps still required on Actions
**Choice:** Macros return `list[Op]`; they do not mint Caps. The `@action(..., caps=...)` that *calls* the macro remains responsible for Cap policy.

**Why:** Cap law is Host/Action concern. Macros are not a security boundary.

---

## 10. Process and quality

### D10.1 — Council seats and halt-or-patch
**Choice:** Law, Channel, Document, Domain, Design, Author, Adversary + Scribe; strategy halt-or-patch; prompts as artifacts patched in place.

**Why:** Inherited from ux-app COUNCIL.md / META. Prevents quality drift and prompt sprawl.

### D10.2 — CORNERS as immune system
**Choice:** Pre-mortem rows for token fights, sub-44 targets, Alpine-for-chrome, banned names, undriven pairs, etc. Append-only found corners.

**Why:** Antifragile loop: stress leaves a scar in artifacts + tests.

### D10.3 — Tests for ports without full Channel
**Choice:** Unit tests stub `ux_app.ops.Op` and assert pair shapes / payloads; no live Channel required.

**Why:** Fast, isolation-safe, runnable in artifact sandbox. Integration tests against full App.bind remain a promote-time concern.

### D10.4 — Kill criteria (non-negotiable)
- Channel/CEK import outside adapter/**
- Action succeeds without required Cap when Cap required
- Illegal / undeclared pairs on the wire
- Preview writes authority kv; Peer mints Cap
- Money/qty/roles on client plane
- Second design system or second kernel
- Banned name in public `__all__`
- Alpine for open/selected when Channel path exists
- Component marked done without tokens + Channel note + ownable path
- Visual craft that requires Host to override token surfaces with local CSS as the only path

---

## 11. Alternatives considered and rejected (summary)

| Alternative | Rejected because |
|-------------|------------------|
| Alpine-default Dialog/Tabs | Violates minimal client surface; user required Channel chrome |
| Raw Op batches in every product Action | Not intent-level; duplicates design patterns |
| Tokens owned by ux-app | Second design system; Document ownership is ux-dom |
| Public module/API named `chrome` | Banned in isolation.py |
| Multi-overlay cells as default | Breaks one-cell Host law; harder focus/morph identity |
| CSS-in-JS or React design system | Outside stack law (Python + Tailwind + Channel) |
| Closed Effect catalog | Domains must stay first-class; notify stays S-only |
| App-scoped DI for ports in v1 | Unnecessary complexity for current Host model |
| Claiming full shadcn inventory shipped | Honesty: deferred components listed in D8.4 |

---

## 12. Explicit non-goals

- Not a Figma token pipeline (may be added later; not chosen now)
- Not visual regression CI in this artifact package (promote-time)
- Not rewriting live bitplorer HEAD in this sandbox (promote by copy/PR)
- Not supporting Peer-minted Caps or client-writable money
- Not replacing Cap/stamp/doctor machinery

---

## 13. Supersession

To change any decision above:

1. Add a dated subsection under **Supersessions** with: old decision id, new choice, reason, migration impact.
2. Update MASTER / ARCHITECTURE / CHROME_API / code in the same change.
3. Add or adjust CORNERS + tests if the change could regress.

### Supersessions

#### S1 — 2026-08-17 — Inventory completion
**Supersedes:** D8.4 deferred list (partial).
**New choice:** Ship Slider, Progress, Avatar, ToastHost, Sheet, Breadcrumb, Pagination, RadioGroup, Kbd, DatePicker, StatusStrip in the elevated package.
**Why:** User requested completing the design system; core battery beyond foundation is required for drop-in use.
**Still deferred (explicit):** Carousel, Chart, Popover, DropdownMenu, Command, NavigationMenu, Sidebar, DataTableView, SearchCombobox as dedicated component modules — behavior partially covered by macros + existing composites.

---

## 14. Index of related artifacts

| Artifact | Role |
|----------|------|
| `MASTER_DESIGN_SYSTEM.md` | Locked product contract |
| `ARCHITECTURE_INTERFACES.md` | Ports/adapters composition |
| `CHROME_API.md` | Author chrome surface + elevation rule |
| `CORNERS.md` | Pre-mortem / found defects |
| `CRITICAL_INSIGHTS.md` | End-to-end review findings |
| `IMPLEMENTATION_STATUS.md` | Phase completion + promote path |
| `COMPONENTS.md` | Component inventory for authors |
| `ux_app/ports.py` | Protocol definitions |
| `ux_app/adapters.py` | Channel adapters + key scheme |
| `ux_app/overlay.py` | Author façade macros |
| `ux_dom/ui/tokens.py` | Elevated token tables |
| `ux_dom/ui/*.py` | Elevated / Channel-first components |
| `OWNERSHIP_COUNCIL.md` | Binding placement matrix (what lives where) |

---

**End of decision record.** If it is not written here, it is not an agreed design choice.

#### S2 — 2026-08-17 — Ownership council
**Adds:** Binding placement matrix in `OWNERSHIP_COUNCIL.md`.
**Choice:** Markup/tokens → ux-dom only; Op chrome macros/ports → ux-app only; Cap/wire → Channel via adapter; product flows → Host.
**Why:** Long-term stability requires one home per kind of truth; dual ownership was the top adversary failure mode.
