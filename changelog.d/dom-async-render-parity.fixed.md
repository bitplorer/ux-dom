- **Fix: ``__async_render__`` matches ``__render__``.** CSS tags (``CSSClass``,
  ``CSSId``, ``Keyframes``) and a ``ReactiveComponent`` changed after construction
  now stream the same HTML as sync render. ``previousSibling`` of a first child
  is ``None``. ``body=`` assets follow the head rules: a ``name``/``content``
  dict is a ``<meta>`` and ``.CSS`` is a stylesheet. An explicit
  ``tag="link"``/``"css"`` still wins in body.
- **Fix: async ``pretty=True`` no longer reflows non-pretty roots.** A ``pre``,
  ``style``, ``br`` or ``wbr`` rendered at top level with nested tags used to
  stream indented children, which changed the whitespace inside ``<pre>``. It now
  matches ``__render__`` (children stay compact).
