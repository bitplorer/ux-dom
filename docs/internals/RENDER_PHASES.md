# Render phases — no double “render” mystery

ux-dom uses **two different words that look the same** but are not:

| Name | When | What it does | How often |
|------|------|--------------|-----------|
| **`Component.render(*args)`** | **Build** (constructor) | Returns the child tree for this component | **Once** per instance (unless Reactive re-render) |
| **`dom_tag.__render__` / `_render` / walk** | **Serialize** (`str`, StreamingResponse) | Walks the finished tree → HTML tokens | Once per serialize call |
| **`HtmlDocument.__pre_render__`** | Start of serialize | Mutates tree (XElement defs, charset, …) | Once per serialize call |

## What is *not* a double bug

```text
Page = Component → render() builds div(…)     # phase BUILD
str(page)        → __render__ walks tokens    # phase SERIALIZE
```

Calling `str` twice does **not** call `Component.render` again.  
Building an XElement host does **not** re-run definition `render` (registry SSoT).

## Real paths that *can* re-run build `render`

1. **`ReactiveComponent`** — intentional: state change → `_re_render()` → `render()` again.
2. **Manual** `Component.__init__` / reconstructing the component.

## Serialize guards (locked by tests)

| Path | pre_render | Component.render |
|------|------------|------------------|
| `str(document)` | 1× | 0× extra |
| `__async_render__(pretty=False)` | 1× | 0× extra |
| `__async_render__(pretty=True)` | 1× (not 2×) | 0× extra |
| N hosts of same XElement | definition `render` 1× total | |

## Historical worry (dom_tag “double render”)

People see `_render` inside `_walk_render_tokens` when `pretty=True` and think the whole page builds twice. That path only **serializes** twice in the sense of one full layout walk — it does **not** re-call `Component.render`.  

A past footgun: `__pre_render__` only on `_render`, so streaming (`pretty=False`) skipped definition collection. Fixed by calling pre-render on the compact walk too, without double-calling when pretty delegates to `_render`.

## Mental model for authors

```python
class Card(Component):
    def render(self, title):          # BUILD once
        return div(h1(title), ...)

html = str(Card("Hi"))               # SERIALIZE — does not call render again
```

```python
class Hello(CustomElement):
    tag_name = "hello"
    def render(self, tag_name="hello"):  # BUILD definition once per class
        return template(..., **{"x-tagname": tag_name})

Hello()  # host; definition.render already done
```


See also [MEMORY_TREE.md](MEMORY_TREE.md) (lazy membership vs list-backed tree).
