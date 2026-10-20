- **BREAKING: `dom_tag.add_raw_string(s)` removed.** Use `node.add(raw(s))`
  (`from ux_dom.dom import raw`). The old method (inherited from dominate's 2012
  escape hatch) appended `s` unescaped with no parent link, rendered outside a
  Component's root, and accepted `None` only to fail at render time. `raw()`
  goes through `add`, so ownership and Component delegation are correct. No
  caller existed in ux-dom or any sibling repo.
