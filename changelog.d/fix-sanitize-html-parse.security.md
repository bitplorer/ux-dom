- **Security: string→HTML parse always strips runnable markup.** `defHTML` /
  `Fragment(str)` / `Component.render()->str` / `HTMLElement` / `JinjaElement` /
  `MarkdownElement` drop `script`/`iframe`/`style`/…, `on*`, Alpine `x-*`/`@*`/`:*`,
  `hx-on*`, and `javascript:`/`vbscript:`/`data:text/html` URLs (and dangerous
  `style=` values). `escape=False` no longer keeps those; `raw()` is the
  verbatim opt-out. Safe tags and attributes are kept.
- **Security: string→HTML is an allowlist.**
  `defHTML` / `Fragment(str)` / `Component.render()->str` / `HTMLElement` /
  `JinjaElement` / `MarkdownElement` / `to_fragment(str)` / `srcdoc` share one
  sanitizer. Known-safe tags and per-tag attributes are kept. `script` /
  `iframe` / `object` / `embed` / math / SVG animation are dropped with their
  children. Unknown tags (`portal`, custom elements) are removed and their
  children kept. `on*`, `hx-*`, `data-hx-*`, and Alpine `x-*` / `@*` / `:*`
  do not survive. `raw()` is still the verbatim opt-out.
- **Security: no mutation XSS through raw-text elements or comments.**
  `<noscript><!-- </noscript><img src=x onerror=alert(1)> --></noscript>`
  emitted a live `<img onerror>` (a browser reads `noscript` as raw text).
  `noscript`, `noembed`, `noframes`, `xmp`, `plaintext`, `iframe`, and
  `template` are now dropped with their content, and comments are dropped.
- **Security: untrusted input cannot select document mode.** A string starting
  with `<html>` kept `<link rel=stylesheet href=https://evil…>`, `<style>`
  (CSS exfiltration) and `<meta http-equiv=set-cookie>`.
