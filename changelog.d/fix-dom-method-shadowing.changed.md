- **BREAKING: internal DOM mutators renamed with a leading underscore:**
  `clear` → `_clear`, `remove` → `_remove`, `set_attribute` → `_set_attribute`,
  `delete_attribute` → `_delete_attribute`, `setdocument` → `_setdocument`,
  `replace_children` → `_replace_children`. Item syntax is unchanged:
  `node["k"] = v` / `del node["k"]` / `node[0] = child`.
  *Migration:* call sites use the `_` name (or item syntax).
- **BREAKING: defining an old mutator name on a tag/Component fails loud.**
  A subclass (or a mixin earlier in its MRO) that defines `clear`, `remove`,
  `set_attribute`, `delete_attribute`, `setdocument` or `replace_children`
  raises `TypeError` at class creation; before, the override would have been
  silently ignored. *Migration:* override the `_` name (`_set_attribute`,
  `_clear`, …), which is the supported extension hook, or rename the method.
- **BREAKING: `get` / `matches` are sealed.** Defining either on a `dom_tag`
  subclass, or inheriting it from a mixin earlier in the MRO (instance method,
  classmethod, staticmethod, or attribute such as a dataclass field
  `matches: int = 0`), raises `TypeError` at class creation. *Migration:*
  rename it (e.g. `get_view`, `on_get`); to customize tree queries override
  `_find` / `_matches`.
- **BREAKING: overriding `add` no longer customizes every attach path.** It
  now affects only explicit `.add()` calls; constructor args, `with` and `+=`
  call `_add`. *Migration:* override `_add` to customize attachment.
