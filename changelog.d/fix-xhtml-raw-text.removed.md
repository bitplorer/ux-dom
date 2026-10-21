- **BREAKING: the ``xhtml`` render parameter is removed (#87).** ``__render__``,
  ``__async_render__`` and the internal ``_render`` / ``_walk_render_tokens`` /
  ``_render_children`` hooks no longer take it; output is HTML only. ``xhtml=True``
  only wrote void elements as ``<br/>``, and served as ``application/xhtml+xml``
  its output was not XML: ``<style>`` / ``<script>`` bodies stayed raw, so
  ``a < b`` or ``&&`` broke the page and well-formed markup in a body ran in
  Chromium. Nested ``title`` / ``textarea``, bare attributes and ``--`` in
  comments did not parse either, and no XHTML namespace was written. No caller
  passed it in ux-dom or any sibling repo; ux-motion's render overrides drop the
  parameter in the same train.
