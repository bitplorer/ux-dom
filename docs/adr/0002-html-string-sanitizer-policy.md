# ADR 0002 — HTML String Sanitizer Policy

> **Diátaxis:** ADR · **Canonical:** `docs/adr/0002-html-string-sanitizer-policy.md` · **Layer:** ux-dom (string→HTML parse)  
> Map: [INDEX.md](../INDEX.md).

**Status:** Accepted  
**Amended by:** [ADR 0004](0004-no-compat-shims-pre-release.md); [URL values from Python](#amendment-url-values-from-python-86) (2026-10-21)  
**Date:** 2026-10-20  
**Scope:** Every path that parses a markup string into ux-dom nodes: `defHTML`,
`StringToHTML`, `Fragment(str)`, `Component.render()->str`, `HTMLElement`,
`JinjaElement`, `MarkdownElement`, `to_fragment(str)`, `srcdoc` strings, and
`ux_dom.response.sanitize_html` / `sanitize_html_stream` (#121).

---

## Context

PR [#32](https://github.com/bitplorer/ux-dom/pull/32) (audit item F-03) replaced
the deny-list on the string→HTML path with an allowlist. Its review found that:

- Unknown tags are unwrapped, so custom elements such as `<x-counter>` lose
  their tag. Authors need a way to keep a custom element they trust.
- `escape=False` used to keep `<script>` on this path. After #32 it no longer
  does, so the flag means nothing for safety, but callers still pass it.
- The input chose document mode: a string starting with `<html>` kept
  `<link rel=stylesheet>`, `<style>`, and `<meta http-equiv>`.

Evidence for the blast radius (a grep and AST scan of the sibling repos on
2026-10-20, at ux-compose `04994da`, ux-channel `d34448c`, ux-behavior
`09a9a65`, and ux-motion `0adae27`; summarized on PR #32): the sibling repos
make **0 calls** that pass a markup string into ux-dom parsing. Every markup string they hand to ux-dom is wrapped in `raw(...)`, and
their `Component.render()` methods return tag trees.

## Decision

**Choice:**

1. **Unknown elements are unwrapped by default.** The tag is removed and its
   children are sanitized and kept. Custom elements are kept only through an
   explicit allowlist: `defHTML(s, allow_custom_elements=["x-counter"])` or a
   `"prefix-*"` pattern (`["x-*"]`). Each entry must be a valid custom element
   name (lowercase, contains `-`, not a reserved name such as
   `annotation-xml`), so the opt-in cannot re-allow `script` or any built-in
   tag. A kept custom element carries global, `aria-*`, and `data-*`
   attributes only; `on*`, `hx-*`, and Alpine attributes are still dropped.
2. **There is no `escape` parameter.** There is no verbatim mode for
   strings. The ignored `escape` parameter and the `escape_string` switch
   were removed under [ADR 0004](0004-no-compat-shims-pre-release.md)
   ([#59](https://github.com/bitplorer/ux-dom/issues/59)): a string child of
   a tag is text, and string HTML is always sanitized. Trusted HTML uses `raw()` or a `Markup` (`__html__`) value, which never
   enters the parser. Because `Markup` is a `str` subclass, every entry point
   checks `__html__` before `str` (`to_fragment`, `srcdoc`, `Fragment`,
   `Component.render()`).
3. **Document mode is the caller's keyword** (`document=True`). The input never
   selects it. Inside ux-dom only an author's HTML file returned from
   `Component.render()` as a `Path` opts in.
4. **Where Python and a browser parse differently, the construct is dropped.**
   `noscript`, `noembed`, `noframes`, `xmp`, `plaintext`, `iframe`, and
   `template` are dropped with their children, and comments are dropped. A
   document-mode `<style>` keeps its text verbatim and is dropped when that
   text contains `<` or when it sits inside `<svg>` / `<math>` (foreign
   content parses style children as markup). Attribute names outside
   `[a-z][a-z0-9_.:-]*` are dropped rather than left for the renderer to
   refuse.

**Why:** an allowlist that unwraps is the safe default for strings of unknown
origin, and the measured external usage shows no caller depends on the old
behaviour. Each opt-in names exactly what it widens, at the call site.

## Alternatives

| Option | Verdict | Why |
|--------|---------|-----|
| Keep every `x-*` / hyphenated tag by default | Rejected | A third-party custom element can run author JS on upgrade; untrusted input should not choose which ones appear |
| Make `escape=False` mean "verbatim" again | Rejected | Recreates the F-03 bypass; `raw()` already is the verbatim path |
| Remove the `escape` parameter | Rejected at the time; superseded by [ADR 0004](0004-no-compat-shims-pre-release.md), and the parameter is removed | Breaks callers for no safety gain; documenting it is enough |
| Infer document mode from `<!DOCTYPE` / `<html>` | Rejected | Lets attacker input load stylesheets, inject CSS, and set `http-equiv` |

## Consequences

- An author who renders a custom element from a string adds
  `allow_custom_elements=[…]`, or builds a tag tree, or uses `raw()`.
- A `Markup` returned from `MarkdownElement.render()` (or any
  `string_is_markdown` component) is already HTML, so it is emitted verbatim
  and the markdown conversion is skipped. Return a plain `str` to get
  markdown conversion plus sanitizing.
- A document-mode `<style>` is the same raw-text element as a hand-built
  `style(...)`, so the render-time `</style` neutralization (#53) still
  applies to it.
- Comments, `noscript`, and `template` content in string HTML disappear from
  the output.
- `to_fragment(str)` and `srcdoc` strings are always fragment mode: a whole
  page passed there loses its doctype, `meta`, `link`, and `style`.
- Rules and tests: [security/ATTRIBUTES.md](../security/ATTRIBUTES.md),
  `tests/07_resilience/test_html_string_mxss.py`.

## Amendment: URL values from Python (#86)

**Date:** 2026-10-21 · **Issue:** [#86](https://github.com/bitplorer/ux-dom/issues/86)

**Context.** `<svg><a><animate attributeName="href" to="javascript:…"/></a></svg>`,
built with ux-dom tags, ran script on click in Chromium (found in
[#85](https://github.com/bitplorer/ux-dom/pull/85)). A Chromium click matrix
over every URL-bearing construct on the tag path (HTML `href`, `src`,
`action`, `formaction`, `iframe`/`object`/`embed`, `meta` refresh, SVG `a`,
`use`, `image`, `feImage`, `script`, MathML `href`, `srcset`, `ping`, …,
with case, space, control-character, tab/LF/CR, entity and `Markup`
variants) found one vector that executed: SVG `animate` / `set` setting `href`
through `to`, `from` or `values`, in every obfuscation except entities (which
the renderer escapes). Everything else was already refused by the URL
allowlist. The locking oracle is
`tests/06_browser/test_svg_animation_url_browser.py`.

**Decision.**

1. **`__html__` / `Markup` means "trusted as HTML", not "trusted as a URL".**
   A `Markup` value in a URL attribute gets the same check as any string.
   `Markup` stays verbatim only where the value is HTML (`srcdoc`, children,
   fragments).
2. **URL values from Python fail closed through an allowlist.** Values passed
   from Python are not author-trusted the way `on*` handler names are: in a
   URL attribute only relative same-origin URLs, `http:`, `https:`,
   `mailto:`, `tel:`, `sms:` and `data:image/{png,jpeg,jpg,gif,webp,avif}`
   pass. Anything else renders as `about:invalid#ux-dom-unsafe-url`. The
   check runs on the final text whatever type was passed: `str(value)`, or
   the JSON text of a list or dict (`values=["#x;javascript:…//"]` renders
   JSON that SMIL splits on `;`, and ran script before this). `sms:`
   and `data:image/avif` were added here because neither can run script.
   `srcset` / `imagesrcset` check each candidate URL the same way: nothing ran
   there in Chromium, but the parse is cheap and keeps it equal to `src`.
3. **Animation values are URLs.** On `animate`, `set`, `animateMotion` and
   `animateTransform`, `to`, `from`, `by` and each `;`-separated item of
   `values` get the URL check, whatever `attributeName` says. Parsing
   `attributeName` (case, XML prefixes, `xlink:href` aliases) is fragile;
   ordinary animation values (`0;1`, `rgb(…)`, `10px`, `#id`) have no scheme
   and pass as relative URLs, so checking them all costs nothing legitimate.
4. **Deliberately refused, opt-in deferred.** `data:image/svg+xml`, `blob:`,
   `ftp:` and custom schemes stay refused. A typed `SafeURL` opt-in is planned
   only when a real caller needs one; no caller in ux-dom or its siblings does
   today.

`meta content` is not checked: a `javascript:` or `data:text/html` refresh URL
did not run in Chromium, and `content` on other `meta` elements is free text.

**Consequences.** `safe_attr_value` takes the element name (`tag`) so the
animation rule can see its element. The full list of checked attributes and
allowed schemes lives in [security/ATTRIBUTES.md](../security/ATTRIBUTES.md),
and `tests/04_production/test_attribute_docs_match_code.py` keeps it equal to
the code. Exact strings: `tests/07_resilience/test_svg_animation_urls.py`.
