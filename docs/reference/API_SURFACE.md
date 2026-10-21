# Public & private API surface (0.2.0)

> **Diátaxis:** reference · **Canonical:** `docs/reference/API_SURFACE.md` · **Layer:** ux-dom  
> Map: [INDEX.md](../INDEX.md).

### Brand lines

| Layer | Name |
|-------|------|
| **PyPI / pip** | `ux-dom` |
| **Import** | `ux_dom` |
| **CLI** | **`uxdom`** (pure-dom tooling only) |

Product lifecycle CLI: **`uxcompose`** (`create-app` · `build` · `serve` · `deploy` · `doctor`).

---

## Top-level (`import ux_dom`)

| Symbol | Kind | Notes |
|--------|------|--------|
| `__version__` | str | e.g. `"0.2.0"` |
| `Document` | class | HTML shell SSoT |
| `Component` / `Fragment` / `ReactiveComponent` | class | Trees |
| `XElement` / `Htmx` / `Csp` / `Channel` | facades | aliases of `ux_dom.plugins` (`XElementRuntime`, `HtmxControl`, `Csp`, `UxChannelRuntime`) |

`WebAssets` and `TailwindCommand` are not on this package. App folders are `from ux_compose import WebAssets`. CSS minify is `uxcompose build`.

---

## DOM (`from ux_dom.dom import …`)

HTML tags, parse helpers, serialize via `node.__render__` / `__async_render__`.

### Stable seam for sibling packages

| Symbol | Kind | Defined in (private) |
|--------|------|----------------------|
| `Component` | class | `ux_dom.dom.src.component` |
| `dom_tag` | class | `ux_dom.dom.src.dom_tag` |
| `escape` | fn | `ux_dom.dom.src.utils.dom_util` |
| `raw` | fn | `ux_dom.dom.src.utils.dom_util` |

Import these from `ux_dom.dom`, not from `ux_dom.dom.src.*`. The `src` layout
is internal and may move; these four names are the supported path.

- **Why:** the siblings reach these four through private paths today:
  ux-compose (`Component`, `dom_tag`, `raw`), ux-channel (`escape`), and
  ux-motion (`Component`). They cover every private `ux_dom.dom.src.*` import
  in the siblings.
- **Status:** the names were already importable from `ux_dom.dom` through the
  star imports. They are now listed here, re-exported explicitly, and pinned by
  `tests/01_core/test_public_dom_seam.py`.
- `ux_dom.dom` has no `__all__` on purpose. A literal list would freeze every
  star-exported name (311 of them, including undecided ones) as public API.

### SVG and MathML tags

- **SVG:** `ux_dom.dom` has a class for every SVG 2 element except `a`,
  `script` and `style`, which are the HTML classes. Names keep their case
  (`linearGradient`, `foreignObject`, `feDropShadow`). Every SVG element is
  written with an end tag.
- **Name collisions:** a tag class gets a trailing `_` when its name would
  shadow a Python builtin on `from ux_dom.dom import *` (`filter_`, `set_`,
  `input_`, `object_`, `map_`; `del_` because `del` is a keyword). It still
  writes its element. There is one deliberate exception, `time_`: `time` is
  not a builtin, but apps very commonly `import time` next to a star import.
  `html`, `code` and `select` also match stdlib module names, but app code
  rarely imports those, so they keep plain names. Lock:
  `tests/07_resilience/test_tag_names_no_builtin_shadow.py`.
- **MathML:** no classes. No caller in ux-dom or its sibling repos builds
  MathML ([#104](https://github.com/bitplorer/ux-dom/issues/104)), so none
  are added ([ADR 0004](../adr/0004-no-compat-shims-pre-release.md)). Author
  MathML with a `Tags` subclass that names its element
  (`class mi(Tags): tagname = "mi"`), or as trusted markup with `raw()` /
  `Markup`. The renderer's namespace model knows MathML integration points
  (`mi` / `mo` / `mn` / `ms` / `mtext`, `annotation-xml`) by name, so such a
  class gets the same raw-text and breakout rules. The string sanitizer drops
  `math`.

## Serialize (`from ux_dom.response.serialize import …`)

| Symbol | Kind | Notes |
|--------|------|--------|
| `to_html_bytes` | fn | Tree / Component / str → UTF-8 HTML bytes |
| `extract_by_id` | fn | Outer-HTML slice for `#id` (C2). `Fragment` builds trees; this extracts. Compose `_fragment_for_target` KEEP until callers USE this. Channel `_guess_target_from_html` is selector leftover — not extract. Not on root `__all__`. |

## Sanitize (`from ux_dom.response import …`)

| Symbol | Kind | Notes |
|--------|------|--------|
| `sanitize_html` | fn | Untrusted HTML `str` → sanitized HTML `str`: exactly the `defHTML` nodes rendered with `pretty=False`, nothing added (no trailing newline). A `Markup` (`__html__`) is returned verbatim. |
| `sanitize_html_stream` | fn | Sync or async iterable of `str` chunks → iterator of the same kind. Joined, the pieces equal `sanitize_html` of the joined chunks, wherever the chunks are split. A `Markup` chunk is verbatim and ends the fragment before it. |
| `HtmlStreamOverflow` | exc | `ValueError`: more than `max_chars` characters arrived without a safe boundary. The held text is not emitted. |
| `MAX_BUFFER_CHARS` | const | Default `max_chars`: `1 << 20` characters. |

A stream is buffered up to safe boundaries: points where the tokenizer has
no open element, tag, comment, raw text or reference. Each stretch between two
is sanitized as one string, so the sanitizer has one policy for strings and
streams ([ADR 0002](../adr/0002-html-string-sanitizer-policy.md)). Time is
linear; memory is the text since the last boundary, at most `max_chars`.
Text with no boundary (one element left open, an unfinished comment, a run
of characters with no space, `;` or `>`) waits for one and fails closed past
`max_chars`.

Memory budget: a stream holds at most `max_chars` characters, which cost
about 1 to 2.5 bytes each for Latin-1 text and up to 10 for emoji (measured
peak, an open element vs an open attribute or comment). At the default that
is 1 to 10 MiB per stream, so 1,000 concurrent streams can hold 1 to 10 GiB;
pass a lower `max_chars` when that is too much. The default is not lower
because a page wrapped in one element is held whole: the largest ux-compose
app page measured holds 66,606 characters, more than 64 KiB (#124).
Input of any nesting depth is handled: end tags are implied as a browser
implies them and the parsed tree is at most 512 deep, as in Chromium; nothing
raises `RecursionError` ([security/ATTRIBUTES.md](../security/ATTRIBUTES.md)).

HTTP adapters (`HTMLResponse`, …) stay optional. Product delivery is ux-compose.

---

## Document shell

```python
document = Document(...).use(XElement(), Htmx(), Csp.auto())
html = str(document(page_content))  # or tree.__render__()
```

Product HTTP delivery / host strategy: **ux-compose**, not Document.use.

---

## Discovery

Product page routing is **ux-compose** (`ux_compose.routing.DirectoryRoutes`).
This package ships no file router: `ux_dom.routing` was removed (F-18).

---

## CLI (`uxdom` — pure-dom only)

| Command | Role |
|---------|------|
| `doctor` | Package / Document health |
| `lint` | Conventions |
| `profile` / `dashboard` | Render p95 |
| `add` | component \| xelement \| ui |
| `ui` | List UI kit |

**Product CSS is `uxcompose build`.** Product verbs create-app · build · serve · deploy live on **uxcompose**.

---

## Private / do not depend on

* Underscored render internals
* `docs/archive/*`
* Deleted product shells (`WebAssets`, `TailwindCommand`, `CreateProject`, host / HMR plugins) are absent — not fail-closed classes
* `ux_dom.routing`, `DirectoryRouting`, `App.routes()`, `uxdom add route` — removed (F-18)
