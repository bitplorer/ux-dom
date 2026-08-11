# ReactiveComponent

Server-side **stateful** component: when dataclass fields change, the next
render (or `str()`) re-runs `render()` with updated state.

## Natural API (preferred)

```python
from dataclasses import dataclass
from ux_dom import ReactiveComponent
from ux_dom.dom import div, button

@dataclass(eq=False)
class Counter(ReactiveComponent):
    count: int = 0

    def render(self, count=0):
        return div(f"Count: {count}", id="c")

    def increment(self):
        self.count += 1

c = Counter(count=0)
c.increment()
assert "1" in str(c)
```

## Rules

1. Declare reactive fields as **dataclass fields**.
2. Mirror them as **`render` parameters** (same names).
3. Mutate fields on the instance; serialize / `str()` triggers re-render.
4. Do **not** name methods `add` if you need `Component.add` for children —
   use `increment` / `bump` / etc.

## Alternate pattern (``super().__init__``)

```python
@dataclass(eq=False)
class StateElement(ReactiveComponent):
    a: int
    def __post_init__(self):
        super().__init__(a=self.a)
    def render(self, a):
        return p(a=a)
```

Prefer the natural API without a custom `__post_init__`.

## Internals

- State snapshot: `_ux_dom_states` (not DOM attributes).
- Re-render preserves parent slot and extra children appended after the root.
- Avoid deep graphs of ReactiveComponent embedding Document (historical
  `to_dict` / deepcopy recursion).

See also [COMPONENTS.md](COMPONENTS.md).

## Fail-closed re-render (0.1 hardening)

1. **`render()` runs before the old tree is cleared.** If `render` raises, the
   previous DOM tree and parent slot remain usable.
2. **Multi-root** (`return [a, b]`) always uses `_entry is self` — never a bare
   list (that used to break on the next update with `list has no attribute add`).
3. **Re-entrancy:** nested updates during an in-flight re-render are ignored
   (prevents storm loops from `set_attribute` / render hooks).
4. **Extras:** children appended onto a single-root entry after first paint are
   preserved across re-renders when possible.
5. **XSS:** field values still go through normal tag escaping — never treat
   ReactiveComponent as an HTML-trust boundary bypass.

## Concurrency

Concurrent mutations of one instance are **best-effort** (no full lock). Prefer
one writer per instance; the suite load-tests for crashes, not sequential
consistency under races.

See tests: `tests/01_core/test_reactive_component.py`, `tests/01_core/test_reactive_stress_chaos.py`.
