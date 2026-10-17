# Security Policy

## Supported versions

| Version | Supported |
|---------|-----------|
| 0.2.x   | Yes (best-effort while pre-1.0) |

## Threat model

**ux-dom renders.** It turns Python trees into HTML / streams and stamps a Document shell. It does **not** own Intents, Caps, or product authorization.

| In scope | Out of scope |
|----------|----------------|
| Nonce CSP (`Csp.auto()`, `docs/security/CSP.md`) | Capability checks (`ux-channel`) |
| Safe package static | MorphState / `@action` (`ux-behavior`) |
| Script-injection policy | Product deploy auth (`ux-compose`) |
| Asset / `javascript:` URL policy | Encryption, sessions, cookies |
| Text-by-default strings, `defHTML` sanitizer, safe Markdown (`docs/security/HTML_CONTENT.md`) | |
| Same-origin htmx request URLs (`docs/security/ATTRIBUTES.md`) | |
| Pinned CDN scripts with SRI (`docs/security/CSP.md`) | |

Plain strings are escaped text everywhere. Markup is an explicit opt-in (`Markup`, `raw`, `defHTML(..., escape=False)`); passing untrusted input to an opt-in is a caller bug. Any other path that renders a string unescaped is a library bug: please report it.

## Reporting

1. GitHub Security Advisory on [bitplorer/ux-dom](https://github.com/bitplorer/ux-dom/security/advisories/new), or
2. **bitplorer@outlook.com** with subject `ux-dom security`

Do **not** file a public issue for unreleased vulnerability details. We aim to acknowledge within 5 business days.
