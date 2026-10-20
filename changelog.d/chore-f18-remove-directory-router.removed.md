- **BREAKING (F-18): the pure-dom file router is gone.** Removed ``ux_dom.routing``
  (``DirectoryRouter``, ``StreamingRoute``, ``HTMLRoute``), ``ux_dom.plugins.routing``
  (``DirectoryRouting``), ``RoutingPlugin``, ``App.routes()`` / ``use_routing`` /
  ``add_routing``, and the ``directory_router_*`` diagnostics. Product page routes
  are ``ux_compose.routing.DirectoryRoutes``.
- **BREAKING: ``uxdom add route`` removed** (it now exits 2 like any unknown kind);
  ``add --methods`` removed; the router lint rule removed.
- **BREAKING: ``Component.__getattribute__`` hook removed** (``_DOM_INSTANCE_API``).
  It only existed so route-verb classmethods (``get``, ``add``, ``clear``, …) did not
  shadow the instance DOM API. Do not define those classmethods on a Component.
- Deleted the router demos ``examples/ux_dom_only/hypermedia_shop`` and
  ``examples/standalone_showcase``. ``examples/xelement_kit``, ``examples/ux_kit``
  and ``standalone/htmx_stream_app`` now use explicit FastAPI routes.
- Removed the ``RouteVsDom`` TLA+ spec (it modelled the removed hook).
