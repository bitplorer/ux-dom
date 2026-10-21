- **``ux-bridge.js`` is opt-in.** ``ux_channel_static`` and ``UxChannelRuntime``
  (``ux_dom.Channel``) default to ``bridge=False``, so a page no longer loads
  ``ux-bridge.js`` unless the app passes ``bridge=True``. That script runs any method a
  ``bridge.call`` op names on a bridged widget instance, so pages without bridges must
  not ship it. Apps that mount ux-channel bridges pass ``Channel(bridge=True)``. Lock:
  ``tests/02_document_plugins/test_channel_bridge_opt_in.py``.
