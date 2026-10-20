- **Security: CSS rule nodes never write into HTML context.** A `CSSClass` /
  `CSSId` / `CSS` / `Keyframes` / `CSSProperty` rule writes its selector raw, so
  under `div` (or any element but `style`) a Python-assigned selector such as
  `<img src=x onerror=…>` ran. Rendering one there now raises
  `InvalidNodeContext` (a `ValueError`, next to `InvalidTagName`), in sync and
  async, pretty and compact output. A tag returned by `lazy` renders as a child
  at the lazy's position, so `div(lazy(lambda: rule))` raises too. Inside
  `style`, nested in another rule, through `rule & rule`, or standalone
  (`str(rule)`) is unchanged.
