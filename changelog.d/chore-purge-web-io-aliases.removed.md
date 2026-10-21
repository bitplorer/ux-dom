- **web_io aliases (ADR 0004).** Removed the ``HtmxEvents.hx_get_events`` property (use
  ``get_events("hx-get")``) and the ``MESSAGE`` alias: ``ux_dom.web_io`` now exports
  ``Message``. Lock: ``test_web_io_aliases_absent.py``.
