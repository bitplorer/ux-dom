# ux-dom in one page

Low cognitive load: **render vs product**.

```text
┌─────────────────────────────────────────────────────────┐
│  PRODUCT  (ux-compose)                                   │
│     uxcompose create-app · build · serve · deploy        │
│     App.mount · DirectoryRoutes                          │
└──────────────────────────▲──────────────────────────────┘
                           │ uses render
┌──────────────────────────┴──────────────────────────────┐
│  DOCUMENT SHELL                                          │
│     Document.use(control, runtime, CSP, style)           │
│     serialize: __render__ / __async_render__             │
└──────────────────────────▲──────────────────────────────┘
                           │ renders
┌─────────────────────────────────────────────────────────┐
│  CORE                                                    │
│     Component · tags · XElement · slots                  │
└─────────────────────────────────────────────────────────┘
```

See [SYSTEM.md](SYSTEM.md).

## What you touch day-to-day

| Want | Do |
|------|-----|
| New app | `uxcompose create-app myapp && cd myapp && uxcompose build && uxcompose serve app:asgi` |
| New page | `routes/<stem>.py` (product) or `uxdom add route` (pure-dom stub) |
| Custom element | `uxdom add xelement Counter` |
| UI primitive | `uxdom add ui Button` (ownable copy) |
| Ship | `uxcompose build` · `uxcompose deploy` |
| Live regions | `pip install ux-channel` behind ux-compose `wire/` |

## Non-negotiable rules

1. **Core never imports FastAPI/Tailwind/channel** — adapters and compose do.
2. **Browser surface via Document.use** — not ad-hoc globals.
3. **`[id]` folders stay `[id]` on disk** — FastAPI path becomes `{id}`.
4. **Product CLI is uxcompose** — this layer renders; it does not own product lifecycle.
