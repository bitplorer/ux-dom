- **SVG 2 element classes (#104):** ``discard``, ``feDropShadow``,
  ``feFuncA`` / ``feFuncB`` / ``feFuncG`` / ``feFuncR``, ``feMergeNode``,
  ``foreignObject``, ``metadata`` and ``set_`` (writes ``<set>``; the ``_``
  keeps the builtin ``set`` free). Each is written with an end tag.
  ``foreignObject`` stays an HTML integration point. MathML gets no classes:
  nothing builds MathML today (see ``docs/reference/API_SURFACE.md``).
