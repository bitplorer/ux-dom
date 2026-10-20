- **BREAKING: internal-only DOM mutators renamed with a leading underscore:**
  `clear` → `_clear`, `remove` → `_remove`, `set_attribute` → `_set_attribute`,
  `delete_attribute` → `_delete_attribute`, `setdocument` → `_setdocument`,
  `replace_children` → `_replace_children`. Item syntax is unchanged:
  `node["k"] = v` / `del node["k"]` / `node[0] = child`.
