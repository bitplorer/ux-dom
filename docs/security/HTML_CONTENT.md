# HTML content: text by default

A plain `str` in a tree is **text**. It is escaped wherever it appears:
tag children, `Fragment("...")`, and a string returned from
`Component.render()`.

```python
from ux_dom import Fragment

Fragment("<b onclick=x>hi</b>").__render__()
# '&lt;b onclick=x&gt;hi&lt;/b&gt;\n'
```

## Opting in to markup

| You have | Use | What survives |
|----------|-----|---------------|
| Markup you wrote yourself | `markupsafe.Markup(s)` (any object with `__html__`) | Everything, verbatim |
| Your own template text to parse into nodes | `defHTML(s, escape=False)` | Every tag and attribute, comments, Jinja syntax |
| HTML from users, a CMS or an API | `defHTML(s)` | Allow-listed formatting only (below) |
| Markdown | `MarkdownElement(s)` | Markdown output; raw HTML inside it is escaped |

`HTMLElement` and `JinjaElement` treat their own strings as trusted author
markup. Never pass user input to `Markup`, `raw`, `defHTML(..., escape=False)`
or a `MarkdownElement` subclass that sets `escape_string = False`.

## The `defHTML` sanitizer

`defHTML(s)` is an allow-list. It keeps the formatting tags in
`SAFE_TAGS` and the attributes in `SAFE_ATTRIBUTES`, plus `class`, `title`,
`lang`, `dir`, `role` and `aria-*`. Anything else is dropped **with its
content**:

* `<script>`, `<style>`, `<form>`, frames, SVG/MathML, custom elements;
* event handlers (`on*`), Alpine (`x-*`, `@*`, `:*`), htmx (`hx-*`),
  `data-*` and `style`;
* comments and declarations.

URL attributes (`href`, `src`, `cite`) go through `safe_attr_value`; an unsafe
URL drops the attribute. See [ATTRIBUTES.md](ATTRIBUTES.md).

Why drop Alpine and htmx attributes? With those runtimes on the page,
`x-init`, `@click` or `hx-get` are script. A deny-list of `on*` alone is not
enough.

Tests: `tests/07_resilience/test_untrusted_html.py`.
