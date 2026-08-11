# ux-dom UI kit (shadcn-inspired)

Optional **server-rendered** component library. Tailwind utility classes, Python DX.

## Why

| | React shadcn | ux-dom UI kit |
|--|--------------|--------------|
| Runtime | Client React | **Server HTML** |
| Styling | Tailwind | Tailwind (same utility language) |
| Ownable | Copy into repo | `uxdom add ui Button` copies module |
| Interactivity | Client state | HTMX attrs + Alpine + optional **ux-channel** |
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
```

## Components

`Button` · `Input` · `Textarea` · `Label` · `Select` · `Checkbox` · `Switch`  
`Card` (+ Header/Title/Description/Content/Footer)  
`Badge` · `Alert` · `Separator` · `Skeleton` · `Avatar`  
`Table` (+ Header/Body/Row/Head/Cell)  
`Tabs` (Alpine) · `Dialog` (Alpine)

Tokens: `cn()`, `variants()`, `focus_ring`, `radius`.

## Optional uxchannel bridge

```python
from ux_dom.ui.channel_bridge import (
    channel_available,
    stamp_region,
    live_button,
    to_fragment,
    action_button_attrs,
)

# Morph target
stamp_region(Card(...), uid="Cart:panel")

# Action control (signed caps when channel + host present)
live_button("Refresh", action="Cart.refresh", target="Cart:panel")
```

Without `uxchannel` installed:

- Kit still renders fully
- `live_button` emits stub `data-channel-action` attrs
- No hard dependency — optional power-up

With channel: combine `ChannelComponent` / `ch.control` regions with ux-dom kit markup in slots (see uxchannel `AppShell` slots accepting ux-dom fragments via `to_html` / `to_fragment`).

## Example gallery

```bash
PYTHONPATH=.:examples/ux_kit uvicorn app.main:app --app-dir examples/ux_kit --port 8080
```

## Design rules

1. **No React/Vue** — Components are ux-dom `Component` subclasses.
2. **className variants** — strings only; no CSS-in-JS runtime.
3. **Pass-through attrs** — `hx_*`, `x_*`, `data-*` work on roots.
4. **Copy path** rewrites imports to relative (ownable fork).
5. **Channel is a bridge**, not the default import surface.

## Extending

1. `uxdom add ui Button` → edit `app/components/ui/button.py`
2. Or subclass:

```python
from ux_dom.ui import Button

class PrimaryButton(Button):
    def render(self, *a, **k):
        k.setdefault("variant", "default")
        return super().render(*a, **k)
```
