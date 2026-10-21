- **MarkupSafe is a declared dependency.** ``ux_dom.dom.src.ext`` imports
  ``markupsafe.Markup`` at import time but relied on Jinja2 to pull it in. It is
  now declared directly, and a test fails if any unguarded third-party import in
  ``src/ux_dom`` lacks a declaring dependency.
