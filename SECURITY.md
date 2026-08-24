# Security Policy

## Supported versions

| Version | Supported |
|---------|-----------|
| 0.1.x   | Yes (best-effort while pre-1.0) |

## Threat model

**ux-dom renders.** It turns Python trees into HTML / streams and stamps a Document shell. It does **not** own Intents, Caps, or product authorization.

| In scope | Out of scope |
|----------|----------------|
| Nonce CSP (`Csp.auto()`, `docs/security/CSP.md`) | Capability checks (`ux-channel`) |
| Safe package static | MorphState / `@action` (`ux-behavior`) |
| Script-injection policy | Product deploy auth (`ux-compose`) |
| Asset / `javascript:` URL policy | Encryption, sessions, cookies |

If you put untrusted strings into a tree without the library's escaping discipline, you can create XSS. That is a caller bug unless a public render helper dropped escaping.

## Reporting

1. GitHub Security Advisory on [bitplorer/ux-dom](https://github.com/bitplorer/ux-dom/security/advisories/new), or
2. **bitplorer@outlook.com** with subject `ux-dom security`

Do **not** file a public issue for unreleased vulnerability details. We aim to acknowledge within 5 business days.
