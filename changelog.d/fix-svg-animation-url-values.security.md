- **Security: SVG animation values cannot set a `javascript:` URL.**
  `<animate attributeName="href" to="javascript:…">` inside an SVG `<a>` ran
  script on click. On `animate`, `set`, `animateMotion` and
  `animateTransform`, `to`, `from`, `by` and each `;` item of `values` now get
  the URL allowlist, whatever `attributeName` says; a failing value renders as
  `about:invalid#ux-dom-unsafe-url`. `srcset` / `imagesrcset` check each
  candidate URL the same way (#86).
