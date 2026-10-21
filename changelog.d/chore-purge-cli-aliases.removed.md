- **CLI aliases (ADR 0004).** ``uxdom info`` is gone: use ``uxdom doctor``. The second name
  ``ux_dom.cli.ux_dom`` is gone: use ``ux_dom.cli.app``. ``run_profile(open_hint=)`` is gone
  (the hint was always on), and the report key ``flamegraph_hint`` is now
  ``speedscope_hint``. Lock: ``test_cli_aliases_absent.py``.
