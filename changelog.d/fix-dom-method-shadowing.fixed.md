- **Fix: a Component method named `add` no longer hijacks child attachment.**
  `class Cart(Component): @action def add(...)` plus `with Cart(): li()` used to
  call the action with the `li` as its first argument and drop the child; the
  same happened for a `@classmethod add` once the `__getattribute__` hook was
  removed (F-18). Internals (constructor args, `with` exit, `+=`, Component
  delegation, document assembly) now call `_add`; public `add` is a thin,
  overridable alias.
- Internals query with `_find` / `_matches`. Public `get` / `matches` stay and
  are **sealed**: defining either on a `dom_tag` subclass (instance method,
  classmethod, staticmethod or attribute) raises `TypeError` with a rename hint.
