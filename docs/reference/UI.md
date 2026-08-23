# ux-dom UI kit (shadcn-inspired)

> **Diátaxis:** reference · **Canonical:** `docs/reference/UI.md` · **Layer:** ux-dom  
> Map: [INDEX.md](../INDEX.md).

Optional **server-rendered** component library. Tailwind utility classes, Python DX.

## Why

| | React shadcn | ux-dom UI kit |
|--|--------------|--------------|
| Runtime | Client React | **Server HTML** |
| Styling | Tailwind | Tailwind (same utility language) |
| Ownable | Copy into repo | `uxdom add ui Button` copies module |
| Interactivity | Client state | HTMX attrs + **Channel macros** (Alpine last-resort) + optional **ux-channel** |
| Bundle | npm | `pip install ux-dom` (kit included) |

This is a **DX moat**: product UI speed without a JS SPA, still copy-ownable.

## Install / use

```python
from ux_dom.ui import Button, Card, CardHeader, CardTitle, CardContent, Input, Badge

Button("Save", type="submit", variant="default")
Button("Cancel", variant="outline", hx_get="/partial", hx_target="#panel")

Card(
    CardHeader(CardTitle("Hello")),
    CardContent(Input(name="q", placeholder="Search…")),
)
```

CLI:

```bash
uxdom ui list
uxdom add ui Button          # copy into app/components/ui/ (edit freely)
uxdom add ui Card --force
uxdom add ui Slider
uxdom add ui Carousel
```

## Components

`Button` · `Input` · `Textarea` · `Label` · `Select` · `Checkbox` · `Switch` · `Slider`  
`Card` (+ Header/Title/Description/Content/Footer)  
`Badge` · `Alert` · `Separator` · `Skeleton` · `Avatar`  
`Table` (+ Header/Body/Row/Head/Cell/Caption/Empty)  
`Tabs` (Channel-first) · `Dialog` (Channel-first) · `Sheet` · `Carousel` (Channel-first)  
`Command` · `Popover` · `DropdownMenu`  
`ToastHost` (morph-safe notices; server list is authority)  
`DatePicker` (native `type=date`) · `Chart` (SVG sparkline / bar; no Chart.js)  
`Breadcrumb` · `Pagination` · `Kbd` · `EmptyState` · `PageHeader` · `StatusStrip` · `FormSection`

Tokens: `cn()`, `variants()`, `focus_ring`, `radius`, `surface`, `field_classes`, `target` (`min-h-11`).

Every interactive composite ships empty / disabled / invalid states. `className` always overrides.

## Optional uxchannel bridge

```python
from ux_dom.ui.channel_bridge import (
    channel_available,
    stamp_region,
    live_button,
    to_fragment,
    action_button_attrs,
    public_form,
)

# Morph target
stamp_region(Card(...), uid="Cart:panel")

# Action control (signed caps when channel + host present)
live_button("Refresh", action="Cart.refresh", target="Cart:panel")

# Progressive form: HTML POST always; Channel attrs when peer present
public_form(Input(name="sku"), action="cart.add", href="/actions/cart.add")
```

Without `uxchannel` installed:

- Kit still renders fully
- `live_button` emits stub `data-channel-action` attrs
- `public_form` remains a valid POST form
- No hard dependency — optional power-up

With channel: combine `ChannelComponent` / `ch.control` regions with ux-dom kit markup in slots (see uxchannel `AppShell` slots accepting ux-dom fragments via `to_html` / `to_fragment`).

## Local chrome vs authority

| Surface | Local (perception) | Authority (Action → Op) |
|---------|---------------------|-------------------------|
| Tabs / Dialog / Sheet / Carousel | no — `open` / `active` / `index` are render args | yes (`open`, `select`) |
| Toast list | no — morph of `#notices` | yes (`notify`) |
| Search filter typeahead | `preview.filter` | commit Action |
| Slider / DatePicker value | form field | submit Action |

Alpine is last-resort perception only. Doctor fails alpine-for-open when a Channel path exists.

`x_element.js` is the only custom-element runtime. After `ui.dom.morph`, stock scan re-upgrades hosts. App code does not implement re-upgrade.

## Example gallery

```bash
PYTHONPATH=.:examples/ux_kit uvicorn app.main:app --app-dir examples/ux_kit --port 8080
```
