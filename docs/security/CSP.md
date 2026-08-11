# CSP nonces & header policies

## One rule

```python
from ux_dom.plugins import Csp

document.use(Csp.dev())    # create-app / local DX (default knobs if Csp())
document.use(Csp.prod())   # production lock-down
document.use(Csp.report_only())  # observe only
```

| Layer | Job |
|-------|-----|
| **`Csp` middleware** | Create secure nonce · hold for request · set CSP header |
| **HTML render** | Bake `nonce="…"` on `<script>` / `<style>` (`stamp_tree`) |
| **ux-channel** | Only `src` URLs — **does not** manage CSP |

## Flow

```text
HTTP request
    → CspMiddleware: generate_nonce(32) → ContextVar + scope
    → route builds Document / DOM
    → HTMLResponse / StreamingResponse: resolve_nonce → stamp_tree
    → response.start: Content-Security-Policy: … 'nonce-…' …
    → body done: clear ContextVar
```

After stamp, serialize is **read-agnostic** (attributes carry the nonce).

---

## Presets

| Preset | Scripts | Styles | Other |
|--------|---------|--------|--------|
| **`Csp()` / historical** | CDN hosts + nonce + strict-dynamic | nonce + `'self'` | form-action `'self'` |
| **`Csp.dev()`** | CDNs (unpkg, jsDelivr, Tailwind CDN) | + **`style_unsafe_inline`** | DX for Alpine/Tailwind attrs |
| **`Csp.prod()`** | **no CDN hosts** | nonced `<style>` only | `upgrade-insecure-requests`, `worker-src 'self'` |
| **`Csp.report_only()`** | like prod knobs | like prod | header is **Report-Only** (no block) |

```python
# tighten production websockets to your host
Csp.prod(connect_src=["'self'", "wss://api.example.com"])

# custom extra directives
Csp.prod(extra_directives={"frame-src": "'none'", "media-src": "'self'"})

# builder only
from ux_dom.plugins.csp import policy_dev, build_csp_header
build_csp_header(nonce, **policy_dev().header_kwargs())
```

---

## `strict-dynamic` + host allowlists (browser truth)

`script-src` is built roughly as:

```text
'nonce-XXXX'  ['strict-dynamic']  [https://cdn…]  ['unsafe-inline']
```

### Modern browsers (Chrome, Firefox, Safari current, Edge)

When **`'strict-dynamic'` is present** with a **nonce or hash**:

1. Trust starts only from scripts that match the **nonce/hash**.
2. Those scripts may load further scripts (dynamic loader pattern).
3. **Host expressions in `script-src` are ignored** for script execution.
4. **`'unsafe-inline'` is ignored** when a nonce/hash is present (CSP2+).

So with defaults:

```text
https://unpkg.com in the header  ≠  “any unpkg script can run”
```

Unpkg only helps if:

- a **nonced** bootstrap loads it, or  
- the browser is **legacy** and does not understand `strict-dynamic`.

### Legacy browsers (no `strict-dynamic`)

Hosts **do** apply. CDNs in `script_hosts` are real allowlists.  
`'unsafe-inline'` may apply if nonces are not understood.

### Practical rules

| Goal | Setting |
|------|---------|
| Modern + self-hosted | `strict_dynamic=True`, `script_hosts=[]` (`Csp.prod()`) |
| Modern + CDN via nonced tag | `strict_dynamic=True`; CDN hosts optional legacy only |
| Old browser CDN without nonce | `strict_dynamic=False`, list hosts (weaker) |
| Never rely on host list alone under strict-dynamic | Always stamp nonces on entry scripts |

---

## Style policy

| Flag | Effect |
|------|--------|
| default `style-src 'nonce-…' 'self'` | Nonced `<style>` + same-origin stylesheets |
| `style_unsafe_inline=True` (`Csp.dev()`) | Also allows `style="…"` attributes (Alpine/Tailwind DX) |
| prod default | Prefer nonced styles; avoid inline attrs or add flag consciously |

---

## Full knobs (`Csp` / `CspPolicy` / `build_csp_header`)

| Knob | Meaning |
|------|---------|
| `strict_dynamic` | Add `'strict-dynamic'` to script-src |
| `script_hosts` | Extra script origins (legacy / non-strict-dynamic) |
| `style_hosts` | Extra style origins |
| `style_unsafe_inline` | Add `'unsafe-inline'` to style-src |
| `script_unsafe_inline_legacy` | Add `'unsafe-inline'` to script-src (ignored when nonce present in modern CSP) |
| `img_src` / `connect_src` / `font_src` | Fetch classes |
| `form_action` | Where forms may submit (default `'self'`) |
| `frame_ancestors` | Clickjacking (`'none'`) |
| `base_uri` / `object_src` | Base tag / plugins |
| `upgrade_insecure` | `upgrade-insecure-requests` |
| `report_uri` | Violation endpoint (legacy reporting) |
| `extra_directives` | Any extra `name → value` (e.g. `worker-src`) |
| `report_only` / `is_report_only` | Report-Only header (`Csp.report_only()` preset; field is `is_report_only` on plugin) |
| `debug_header` | `X-ux-dom-CSP-Nonce` (off in prod) |
| `nonce_bytes` | Entropy (default 32) |

---

## What not to do

| Don't | Why |
|-------|-----|
| Mint nonce in channel / routes | Two sources of truth |
| Nonce on static JS responses | CSP keys off the HTML document |
| Cache full HTML with a nonce | Nonce must be unique per response |
| Assume CDN hosts work under strict-dynamic in Chrome | Hosts are legacy fallback only |
| Turn on `debug_header` in production | Leaks nonce in a debug header |

---

## Tests

- `tests/test_csp_nonce.py` — middleware + stamp  
- `tests/test_csp_resolve_nonce.py` — read-agnostic resolve  
- `tests/test_csp_policies.py` — presets, strict-dynamic docs locks, knobs  


## Scaffold / create-app (low cognitive load)

`uxdom create-app` wires CSP for you::

    # app/document.py (generated)
    document.use(XElement(), Htmx(...))
    if settings.WITH_CSP:
        document.use(Csp.auto(debug=settings.DEBUG))

| DEBUG | Policy |
|-------|--------|
| `1` (default) | ``Csp.dev()`` — CDN hosts + style attributes |
| `0` | ``Csp.prod()`` — no CDN hosts, tighter |

No extra mental model: same place as other runtimes (``document.use``),
middleware attaches on ``document.mount(app)``.

```bash
uxdom create-app myapp           # CSP on (auto)
uxdom create-app myapp --no-csp  # opt out
```

Override without fighting the scaffold::

    document.use(Csp.prod(connect_src=["'self'", "wss://api.example.com"]))
