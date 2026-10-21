- **XElement shadow attribute (ADR 0004).** ``shadowroot`` is the only shadow attribute,
  in Python and in ``x_element.js``. The ``shadowdom`` synonym is gone: a ``WebComponent``
  with only ``shadowdom=`` raises the "requires 'shadowroot'" error, ``x_element.js``
  mounts such a definition in light DOM, and ``shadowdom=True`` is an ordinary boolean
  attribute. Use ``shadowroot="true"|"open"|"closed"``.
- **``x_element.js``: dead ``ws_send`` connect branch removed.** No renderer emits a literal
  ``ws_send`` attribute (``ws_send=`` renders ``ws-send``, the htmx ws extension's attribute),
  and when hand-written HTML did reach it, Chromium threw "Still in CONNECTING state" and
  nothing was sent. XElement WebSocket receive/echo is unchanged.
  Lock: ``test_shadowroot_only.py``; browser: ``test_xelement_shadow_ws_browser.py``.
