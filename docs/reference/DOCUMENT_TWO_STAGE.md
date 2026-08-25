# Document two-stage placement

> **Diátaxis:** reference · **Canonical:** `docs/reference/DOCUMENT_TWO_STAGE.md` · **Layer:** ux-dom  
> Map: [INDEX.md](../INDEX.md).

## Why two stages

Your original design is intentional, not accidental:

| Stage | API | Becomes | Position in HTML |
|-------|-----|---------|------------------|
| **A – init** | `Document(head=…, body=…)` + `.use()` | `common_head` / `common_body` | After page head / **end of body** |
| **B – call** | `doc(*content, head=…, body=…)` | call `head` / `body` | **Start of head** / early body |

```text
<head>
  [B] call head      ← title, page CSS, one-off tags
  [A] common head    ← charset defaults, XElement, channel scripts
</head>
<body>
  *content
  [B] call body      ← page-only scripts
  placeholders
  [A] common body    ← HTMX and other “run after content” scripts
</body>
```

## Where CSP / runtimes belong

| Concern | Right place |
|---------|-------------|
| CSP **middleware** (header + nonce) | `document.use(Csp())` → `mount(app)` — not a DOM node |
| Nonce on **script tags** | Stamped at **call time** on both stages when nonce is set |
| Extra CSP **meta** / debug tag | Callable in the list for that position |
| XElement / channel scripts | Stage A **head** (common_head) via `.use(XElement())` |
| HTMX | Stage A **body** (common_body) via `.use(Htmx())` — after content |
| Page title | Stage B **head** |

```python
Document(
    head=[
        meta(charset="utf-8"),
        # callable evaluated at call time, in common_head position:
        lambda ctx: meta(name="x-nonce", content=ctx["nonce"]) if ctx["nonce"] else None,
    ],
    body=[],
).use(XElement(), Htmx(), Csp())

document(
    page_component,
    head=[title("This page")],  # stage B — first in <head>
)
```

`ctx` always includes `nonce`, `document`. App folders are not a Document
concern (`from ux_compose import WebAssets`).

## Do not flatten

Merging everything into one list and dumping it as `common_head` **destroys**
call-time-first ordering. ux-dom keeps four streams and lets HtmlDocument place them.


## `document.use` vs page-local

| API | Mutates shared shell? | When |
|-----|----------------------|------|
| **`document.use(XElement())`** | Yes | App-wide on the module-level instance |
| **`document.using(Alpine())`** | No (returns copy) | One page needs extra runtimes |
| **`document(*c, use=[Alpine()])`** | No | Same as using, at call time |

```python
# app/document.py
document = Document(head=[...]).use(XElement(), Htmx())

# most pages
return document(page, head=[title("Home")])

# special page
return document.using(SomePageRuntime())(page, head=[title("Special")])
# or
return document(page, head=[title("Special")], use=[SomePageRuntime()])
```

Always **instance** API (`document.use`), never class-level `Document.use` as the story.
