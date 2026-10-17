# UxDom UI kit gallery

Shadcn-inspired components from `ux_dom.ui`: server-rendered HTML styled with
Tailwind classes, no client runtime.

```bash
# from the repository root
uvicorn examples.ux_kit.main:app --reload
# open http://127.0.0.1:8000
```

| File | Role |
|------|------|
| `document.py` | `Document(...).use(Htmx(version="2.0.4"))`, Tailwind play CDN |
| `gallery.py` | One section per component family; `POST /toast` fragment |
| `main.py` | Explicit `HTMLRoute` table, validated query parameters, `document.mount(app)` |

State is a render argument: `/?tab=b`, `/?slide=1` and `/?dialog=1` choose
the active tab, the slide and whether the dialog is open, and plain links
change them. The **Save (htmx)** button posts to `/toast` and swaps in the
returned `ToastHost`.

There is no `Csp` here because the Tailwind play CDN injects `<style>` tags at
runtime, which a nonce CSP blocks. For production, build the CSS and add
`Csp.auto()` (see `examples/showcase`). For ux-channel actions on top of
ux-dom, see `examples/ux_channel_counter`.

Tests: `tests/09_examples/test_ux_kit.py`. Component docs:
[`docs/reference/UI.md`](../../docs/reference/UI.md).
