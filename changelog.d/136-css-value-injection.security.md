- **Security: a CSS value stays one value (#136).** A `CSSClass` / `CSSId` / `CSS` /
  `Keyframes` value or property name that could end its declaration or rule (`;`, `{`
  or `}` outside a string, an unclosed string, unbalanced `()` / `[]`, a comment, a
  newline, a backslash outside a string) raises `InvalidCSSValue` (a `ValueError`).
  Before, `color="red} body{background:yellow"` added a `body` rule and
  `color="red;background:url(//cdn.example/x.png)"` added a declaration. Each URL in
  `url()`, `image-set()`, `src()` or `image()` now gets the URL allowlist in any
  property and in a `style` attribute, not only in a property named `background`;
  a refused one makes the value `about:invalid#ux-dom-unsafe-url`. `background:
  url("https://…")`, which that check refused, renders.
