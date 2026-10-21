- **Untrusted HTML of any depth no longer raises `RecursionError` (#125).**
  `sanitize_html`, `sanitize_html_stream`, `defHTML` and `srcdoc` failed at
  about 494 unclosed tags (`<li>item` x 600), a cheap DoS through
  `ux_dom.response`. The parser now implies end tags as the HTML spec does
  (`p`, `li`, `dt` / `dd`, `option` / `optgroup`, table parts, ruby, headings,
  `button`, `</p>`, `</br>`, breakout from `<svg>` / `<math>`) and caps the
  tree at 512 levels as Chromium does. Parsing, the sanitizer's walk, render
  (sync, async, pretty), `_find` and the layout scan use explicit stacks, so
  author-built trees of any depth render too, and building and rendering stay
  linear. Chromium oracle: `test_tree_construction_browser.py`.
