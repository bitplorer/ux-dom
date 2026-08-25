# SafeStaticFile allowlist — investigation

## Purpose

Expose **pip-owned browser assets** at stable HTTP URLs **without** mounting a
package directory (which would leak `__init__.py`, `.pyc`, etc.).

## Three layers

```text
1. URL allowlist     →  who may be addressed
2. Extension allowlist →  what kinds of files
3. Package containment →  where on disk (resolved path under package root)
```

Only then: **one exact GET route per file**.

## URL allowlist (layer 1)

| Pattern | Used by |
|---------|---------|
| `/ux-dom/static/<file>` | XElementRuntime |
| `/ux-pkg/<plugin>/static/<file>` | third-party `PackageStaticContribution` |
| `/ux-channel/static/<file>` | uxchannel (when `mount_via_ux_dom=True`) |

Rejected examples: `/`, `/app/…`, `/etc/…`, `/static/…`, `..`, spaces, missing extension.

## Extension allowlist (layer 2)

Allowed: `.js .mjs .cjs .css .map .woff .woff2 .ttf .otf .svg .png .jpg .jpeg .gif .webp .ico`

**Denied:** `.py .pyc .so …` and **`.json`** (package metadata leak risk).

## Containment (layer 3)

- `resource` may not contain `..` or absolute paths  
- Resolved file must be under `Path(package.__file__).parent`  
- Blocked FS segments: `.env`, `.git`, `.ssh`, `.aws`, `__pycache__`  
- `read_bytes()` re-checks containment (symlink race defense)

## What is registered today

| Plugin | Default files | Who serves HTTP |
|--------|---------------|-----------------|
| `XElementRuntime` | `ux_dom.scripts/x_element.js` → `/ux-dom/static/x_element.js` | ux-dom SafeStaticFile |
| `UxChannelRuntime` | tags only (`mount_via_ux_dom=False`) | **Channel** mount |
| `UxChannelRuntime(mount_via_ux_dom=True)` | allowlisted channel JS under `/ux-channel/static/` | ux-dom SafeStaticFile |

## Gaps fixed in this pass

| Issue | Fix |
|-------|-----|
| Dead `site-packages` block (packages live there) | Removed; real segments blocked instead |
| Nested URL `/static/vendor/file.js` rejected | Allowed safe subdir segments |
| Loose `/ux-pkg/name/file` without `/static/` | Rejected |
| `.json` serveable if registered | Removed from allowlist |
| `read_bytes` only checked parent dir | Re-checks original `package_root` |

## Fail closed

`collect_served_files` raises `UnsafeStaticError` → **no** static install for that pass (nothing unsafe is mounted).

## Introspection

```python
from ux_dom.plugins.safe_static import allowlist_summary
allowlist_summary()
```
