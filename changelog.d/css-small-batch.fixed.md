- **Fix: `Keyframes(from_=…)` renders a `from` step.** The trailing `_` became `-`,
  so it rendered `from-`, which Chromium drops. A CSS rule's attribute names now
  drop a trailing `_` as they drop a leading one.
- **Fix: a CSS property name must be a CSS ident.** `color`, `-webkit-x` and
  `--x` render; `1a`, `-1a`, `--`, `a.b`, `a:b` and escapes raise
  `InvalidCSSValue`. Before, any name without `;`, `{`, `}` or brackets rendered.
