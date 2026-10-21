- **Fix: ``animateTransform`` is closed and keeps its children (#87).** It was a
  single tag, so ``<animateTransform>`` was written with no end tag. An HTML
  parser leaves a bare SVG start tag open, so it held every sibling after it,
  and its own children were dropped. Only the 13 HTML void elements are now
  written without an end tag: ``param``, ``keygen`` and ``command`` get one
  (``<command>`` is not void in the HTML spec).
