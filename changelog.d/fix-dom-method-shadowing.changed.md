- **BREAKING: internal DOM mutators renamed with a leading underscore:**
  `clear` → `_clear`, `remove` → `_remove`, `set_attribute` → `_set_attribute`,
  `delete_attribute` → `_delete_attribute`, `setdocument` → `_setdocument`,
  `replace_children` → `_replace_children`. Item syntax is unchanged:
  `node["k"] = v` / `del node["k"]` / `node[0] = child`.
  *Migration:* call the `_` name (or item syntax). To customize DOM behaviour
  override `_x` (e.g. `_set_attribute`); the public names are available for
  your own methods and actions (e.g. a `remove` action on a Component).
- **BREAKING: `get` / `matches` are sealed.** Defining either on a `dom_tag`
  subclass, or inheriting it from a mixin earlier in the MRO (instance method,
  classmethod, staticmethod, or attribute such as a dataclass field
  `matches: int = 0`), raises `TypeError` at class creation. *Migration:*
  rename it (e.g. `get_view`, `on_get`); to customize tree queries override
  `_find` / `_matches`.
- **BREAKING: overriding `add` no longer customizes every attach path.** It
  now affects only explicit `.add()` calls; constructor args, `with` and `+=`
  call `_add`. *Migration:* to customize attachment override `_add`; the
  public `add` name is available for your own methods.
