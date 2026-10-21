- **Sanitizer uses the renderer's URL allowlist (#126).** String HTML used a
  denylist (`javascript:`, `vbscript:`, `data:text/html`), so `ftp:`, `blob:`,
  `data:image/svg+xml` and `//host` URLs were kept and then rendered as
  `about:invalid#ux-dom-unsafe-url`. A URL attribute (and each `srcset`
  candidate) is now kept only when the renderer's allowlist accepts it, and the
  denylist is removed.
