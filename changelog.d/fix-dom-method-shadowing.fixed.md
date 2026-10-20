- **Fix: a Component method named `add` no longer hijacks child attachment.**
  `class Cart(Component): @action def add(...)` plus `with Cart(): li()` used to
  call the action with the `li` as its first argument and drop the child; the
  same happened for a `@classmethod add` once the `__getattribute__` hook was
  removed (F-18). Internals (constructor args, `with` exit, `+=`, Component
  delegation, document assembly) now call `_add`.
