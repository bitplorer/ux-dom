# Council Decision — Where Design-System Elements Live

> **Diátaxis:** ADR · **Canonical:** `docs/adr/OWNERSHIP_COUNCIL.md` · **Layer:** ux-dom  
> Map: [INDEX.md](../INDEX.md).

**Date:** 2026-08-17  
**Note (2026-08-19):** the author-layer seat is now **ux-behavior** (verbs `open` / `close` / `select` / `notify`). This record still names `ux-app` as the historical owner of Op macros.  
**Note (2026-08-24):** product CLI (`create-app` / `build` / `serve` / `deploy`) and Tailwind CLI finder are **ux-compose**. Markup / Document / tokens seats below still hold. See [ux-compose FLOW](https://github.com/bitplorer/ux-compose/blob/main/docs/FLOW.md).  
**Question:** For a multi-year stable design system on ux-app / ux-dom / Channel, which elements live in which package — and which never move?  
**Strategy:** halt-or-patch · primary sources · adversary stress  
**Outcome:** Binding placement matrix + non-negotiable rules

---

## 1. Seats (what each optimizes for)

| Seat | Mandate |
|------|---------|
| **Law** | Isolation (Channel/CEK only in `adapter/**`), Cap on mutations, S-pair truth, banned names |
| **Channel** | Stamp, Peer apply, two clocks, minimal client authority |
| **Document** | ux-dom owns markup + Tailwind tokens + create-app; pure server HTML |
| **Domain** | DomainPacks for stamped pairs beyond S; drivers; doctor undriven pairs |
| **Design** | One visual system; tokens; 44px; hierarchy; Channel-first chrome |
| **Author** | Day-1 macros, intent-level Actions, ownable copy, cold import |
| **Adversary** | Dual systems, wrong ownership, key leakage, Alpine re-authority, promote rot |
| **Scribe** | Matrix below is the only agreed placement |

---

## 2. North-star constraint (unanimous)

> A design system that lasts must put **each kind of truth in exactly one place**.  
> Markup truth ≠ Op/macro truth ≠ Cap/wire truth.  
> Crossing those boundaries creates a second kernel or a second design system — both are kill criteria.

---

## 3. Placement matrix (BINDING)

### Legend
- **OWNS** — sole writer of the canonical definition  
- **RE-EXPORTS** — may import and expose for DX; must not fork  
- **CONSUMES** — uses via public API only  
- **FORBIDDEN** — must never define or duplicate here  

| Element | ux-dom | ux-app | Channel / CEK | Host / product app |
|---------|--------|--------|---------------|--------------------|
| **Token tables** (surface, ink, type_scale, target, density, overlay, color, cn, variants) | **OWNS** | RE-EXPORTS via `ux_app.ui` | FORBIDDEN | CONSUMES; local CSS may *extend*, not replace the table |
| **Pure markup components** (Button, Input, Card, Table, Badge, Avatar, …) | **OWNS** | RE-EXPORTS | FORBIDDEN | Ownable *copy* via `uxdom add ui` / `uxapp add ui` into product tree |
| **Channel-bridge helpers** (stamp_region, live_button, public_form, to_fragment) | **OWNS** (`ux_dom.ui.channel_bridge`) | CONSUMES | FORBIDDEN in author package body | CONSUMES |
| **Document / TailwindStyle / create-app** | **OWNS** | FORBIDDEN | FORBIDDEN | CONSUMES |
| **Op, update, notify, go, as_ops, S_PAIRS** | FORBIDDEN | **OWNS** (`ops.py`) | Applied by Peer | CONSUMES |
| **Chrome macros** (open_overlay, close_overlay, select_region, confirm, form_result) | FORBIDDEN | **OWNS** (`overlay.py` façade) | FORBIDDEN | CONSUMES |
| **Ports / adapters for chrome** (OverlayPort, ChannelOverlay, key scheme) | FORBIDDEN | **OWNS** | FORBIDDEN | Tests may bind mocks; production uses defaults |
| **Session key scheme** (`ui.overlay.*`, `ui.select.*`) | FORBIDDEN as public API | **OWNS inside adapters only** | Storage is session/world | Product Actions must **not** hard-code keys |
| **@action, App, follow_up, preview** | FORBIDDEN | **OWNS** | Bound via adapter | CONSUMES |
| **Cap mint / Peer apply / stamp** | FORBIDDEN | Only via **adapter/** | **OWNS** | Never |
| **DomainPack + drivers** (e.g. effects notice) | FORBIDDEN | **OWNS** pack registration + thin helpers | Driver applies on world | `app.use(...)` |
| **Doctor / isolation scan** | Document doctor where applicable | **OWNS** package isolation + App.doctor | Wire doctor at host | Calls doctor in prod profile |
| **Host layout / routes / product Actions** | FORBIDDEN | FORBIDDEN as product truth | FORBIDDEN | **OWNS** |
| **Product-specific composites** (CheckoutFlow, DeskStatus) | FORBIDDEN (unless upstreamed as generic pattern) | Optional generic patterns only | — | **OWNS** when product-specific |

---

## 4. Seat arguments (compressed)

### Law
- Tokens and Button markup cannot live in ux-app: that would force Document imports into the author package’s identity and invite dual CSS.
- Overlay macros cannot live in ux-dom: they construct `Op` and would couple Document to Channel pair vocabulary.
- Session key strings must not appear in product Actions or in ux-dom components — only in ux-app adapters.

### Channel
- Open/selected state that matters for recovery and multi-step must be session cells + morph, not Alpine-only.
- Macros that expand to S pairs are correct; domain-stamped chrome requires `app.use` + driver (same as effects).

### Document
- Live COMPONENTS.md already states: *“Markup and Tailwind tokens live in ux-dom. Ownership does not move.”*
- create-app / Tailwind pipeline only understands ux-dom paths cleanly.
- Channel-bridge stays in ux-dom because it is markup-side progressive enhancement (data attributes + optional stamp), not Cap logic.

### Domain
- `notify` stays S-only in ux-app.ops.
- Rich notice pairs stay in effects DomainPack — not in ux-dom ToastHost (ToastHost only *renders* the list).

### Design
- One token table; Host must not invent a parallel surface language.
- Dialog/Sheet/Tabs **markup** in ux-dom; **open/select behavior** via ux-app macros. Splitting markup vs behavior is intentional and stable.

### Author
- Day-1: `from ux_dom.ui import Button` or `from ux_app.ui import Button` (re-export).
- Day-1 chrome: `from ux_app.overlay import open_overlay` (or re-export on `ux_app`).
- Ownable copy path stays CLI into product tree — never “edit the kernel.”

### Adversary (why dual placement fails)
| Wrong move | Failure mode |
|------------|--------------|
| Tokens in ux-app | Two token tables; Host CSS fights create-app |
| open_overlay in ux-dom | Document depends on Op; isolation story collapses |
| Key strings in product Actions | Rename scheme = rewrite every Action |
| Alpine Dialog as *only* path in design system | Client authority regresses; contradicts Channel-first law |
| Product CheckoutFlow upstreamed as “the” Dialog | Design system becomes product-shaped; other hosts reject it |
| Second package “ux-design-system” | Third owner; version skew; kill criterion |

---

## 5. Long-term stability rules (non-negotiable)

1. **Markup never moves to ux-app.** Re-export only.  
2. **Op-producing chrome macros never move to ux-dom.**  
3. **Session key scheme lives only in ux-app adapters.** Product code uses macros.  
4. **ux_app.ui is always a re-export façade**, not a fork of components.  
5. **Channel/CEK imports only under `ux_app/adapter/**`.**  
6. **Generic vs product:** If a composite encodes one product’s domain (checkout, lots desk), it stays in the Host. Upstream only when three+ independent hosts need the same shape.  
7. **Alpine is not a design-system default** for open/selected; Channel-first components are the elevated path. Historical Alpine Dialog/Tabs in ux-dom may remain for backward compatibility until deprecated by version policy — new design-system docs must not recommend Alpine as the primary path.  
8. **Ownable copy** is the extension mechanism for product branding; forking tokens in the Host without a brand package is discouraged.  
9. **Promote path:** elevated tokens/components → ux-dom; ports/adapters/overlay → ux-app; never a third core package.  
10. **Supersession:** Changing this matrix requires a new council note in this file + MASTER + DESIGN_DECISIONS in the same change.

---

## 6. Concrete “lives where” list (implementers)

### Always ux-dom
```
tokens.py, button, input, textarea, select, checkbox, switch, slider, radio_group,
label, separator, skeleton, progress, kbd, badge, avatar, card, alert, table,
dialog (markup), sheet (markup), tabs (markup), toast, breadcrumb, pagination,
datepicker, empty_state, page_header, status_strip, channel_bridge, chart, carousel (markup)
```

### Always ux-app
```
ops.py (Op, update, notify, go)
overlay.py (open_overlay, close_overlay, select_region, confirm, form_result)
ports.py, adapters.py   # chrome ports + key scheme
action, app, follow_up, preview
effects DomainPack helpers
isolation, doctor integration
```

### Always Channel (via adapter only from ux-app)
```
Cap, Peer, stamp, session apply, wire codecs
```

### Always Host / product
```
Routes, product Actions, desk layouts, domain-specific flows,
brand overrides via className or ownable copy,
app.use("…") registrations for product domains
```

---

## 7. Migration / coexistence note

- **Live** COMPONENTS.md still documents Alpine Tabs/Dialog. Council decision: elevated design system treats Channel-first as the **stable long-term** path; Alpine remains a compatibility/runtime option behind `declare_runtime`, not the ownership home of open/selected truth.
- **Badge** currently appears in both `ux_app.html` and `ux_dom.ui` in live trees — Adversary flags dual Badge. Long-term: single Badge in ux-dom; ux-app re-exports or deletes duplicate.
- **design_system/** artifact package is a **staging** tree for promote, not a third runtime package in production installs.

---

## 8. Verdict (Scribe)

**Approved unanimously under halt-or-patch.**

Long-term stable solution:

| Layer | Owns |
|-------|------|
| **ux-dom** | Visual system + pure HTML components + channel_bridge markup helpers |
| **ux-app** | Author macros, Op expansion, chrome ports/adapters, Actions/App, DomainPacks |
| **Channel** | Capability and wire truth |
| **Host** | Product meaning |

Anything that produces **HTML structure** stays in ux-dom.  
Anything that produces **list[Op]** for chrome/product control stays in ux-app.  
Anything that **mints or applies Caps** stays in Channel (reached only through adapter).  

This split is the multi-year answer. Do not invent a fourth home.

---

## 9. Follow-ups (ordered)

1. Promote elevated `ux_dom.ui` tokens + Channel-first Dialog/Sheet/Tabs into ux-dom.  
2. Promote `ports` / `adapters` / `overlay` into ux-app; re-export macros from `ux_app`.  
3. Resolve dual Badge (`ux_app.html` vs `ux_dom.ui`) in favor of ux-dom.  
4. Update live COMPONENTS.md Alpine language to match Channel-first preference order.  
5. Add isolation/doctor checks that product modules do not import adapter private key constants.

**End of council record.**
