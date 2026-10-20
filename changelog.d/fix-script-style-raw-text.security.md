- **Security: `script` / `style` bodies cannot close their element.** At render
  time (sync and async, pretty and compact) the joined body is neutralized,
  case-insensitively: `</script` → `<\/script` and `<!--` → `\u003C!--` (a JS/JSON string escape) in
  scripts, `</style` → `<\/style` in styles (`neutralize_raw_text`). Hazards
  split across children, added later, set by index, or formed with a `raw()`
  child are caught. Both forms stay valid JS, JSON (`application/json`,
  `importmap`) and u-flag regex.
