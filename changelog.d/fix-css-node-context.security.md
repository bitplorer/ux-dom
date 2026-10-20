- **Security: CSS rule nodes never write into HTML context.** A `CSSClass` /
  `CSSId` / `CSS` / `Keyframes` / `CSSProperty` rule writes its selector raw, so
  under `div` (or any element but `style`) a Python-assigned selector such as
  `<img src=x onerror=…>` ran. Rendering one there now raises `TypeError`
  (sync and async, pretty and compact). Inside `style`, nested in another rule,
  through `rule & rule`, or standalone (`str(rule)`) is unchanged.
