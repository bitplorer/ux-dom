- **BREAKING: HTMX / Alpine support is attribute rendering only; the second transport
  is gone.** ux-channel owns transport. Removed: ``ux_dom.web_io`` (``WebSocketAdapter``,
  ``WebSocketClientHandler``, ``WebSocketEvents``, ``HtmxEvents``, ``WebSocketProtocol``),
  ``ux_dom.dom.src.ws_rpc``, ``ux_dom.htmx`` (``HtmxRoutes``, ``HtmxMiddleware``,
  ``HtmxDetails``), the ``ux_dom.Htmx`` / ``HtmxControl`` runtime (htmx CDN script tags,
  partial policy, middleware mount), ``App.htmx()``, ``standalone/ws_app``, the
  realtime_kit WebSocket counter and the ``WebSocketIsolation`` TLA+ spec. ``hx_*`` kwargs
  still render as ``hx-*`` attributes. ``ux_dom.alpinejs`` (``DataSet``, ``dataset_*``)
  stays as an opt-in module that ``import ux_dom`` never loads. Load htmx with your own
  ``script(src=…)`` and read the ``HX-Request`` header in your route. Lock:
  ``test_htmx_alpine_opt_in.py``.
