- **BREAKING: `uxdom build` is gone (ADR 0003 rule 4; #109).** With the bundle removed
  (#101), its ``app/main.py`` step could not fail, ``static-sync`` and ``x_element.js``
  repeated ``uxdom doctor``'s ``x_element.js`` row, and the one real step imported the
  user's app. ``ux_dom.cli.build`` (``run_build``, ``BuildReport``, ``BuildStep``,
  ``format_build_report``) and ``ux_dom.cli.static_assets`` (``sync_runtime_assets``,
  ``SyncReport``, ``SyncedFile``) are removed with it. Use ``uxcompose build``, which
  imports the app (``import:app:asgi``); ``uxdom doctor`` still checks the installed
  ``x_element.js``. Lock: ``test_build_command_absent.py``.
