- **BREAKING: `uxdom build` is gone (ADR 0003 rule 4; #109).** With the bundle removed
  (#101), its ``app/main.py`` step could not fail, ``static-sync`` and ``x_element.js``
  repeated ``uxdom doctor``'s ``x_element.js`` row, and the one real step imported the
  user's app. ``ux_dom.cli.build`` (``run_build``, ``BuildReport``, ``BuildStep``,
  ``format_build_report``) and ``ux_dom.cli.static_assets`` (``sync_runtime_assets``,
  ``SyncReport``, ``SyncedFile``) are removed with it. Use ``uxcompose build``, which
  imports the app (``import:app:asgi``); ``uxdom doctor`` still checks the installed
  ``x_element.js``. Lock: ``test_build_command_absent.py``.
- **BREAKING: ux-dom writes no asset files (#109).** ``PluginHub.materialize``,
  ``PluginHub.all_artifacts``, ``PluginHub.served_static_files``,
  ``App.materialize_assets``, ``MaterializeReport``, ``MaterializedFile`` and
  ``StaticArtifact.bytes`` are removed. Nothing but ``uxdom build`` / ``static_assets``
  reached them. Mounted package files are ``safe_static.collect_served_files(hub)``.
- **BREAKING: no ``serve="dual_copy"`` (#109; AGENTS.md "What not to invent").** With
  the writer gone its ``/assets/…`` tags pointed at files nothing wrote. The ``serve``
  parameter of ``XElementRuntime``, ``UxChannelRuntime``, ``PackageStaticContribution``,
  ``static_from_package`` and ``ux_channel_static`` is removed (passing it is a
  ``TypeError``), with ``ServeMode``, their ``artifacts()`` methods,
  ``package_static.loader_for`` / ``resolve_package_resource``,
  ``PackagedFile.disk_path_under_assets`` / ``public_path_webassets``, the
  ``StaticArtifact.disk_path`` / ``loader`` fields and ``artifact_from_path`` /
  ``artifact_from_callable``. Library JS is served only from the package mount
  (``/ux-dom/static/x_element.js``). Lock: ``test_no_deprecations.py``.
