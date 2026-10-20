- **`uxdom doctor` checks no product readiness (ADR 0003 rules 3 and 4).** The ``--prod``
  and ``--port`` options of ``uxdom doctor`` / ``uxdom info`` are gone, with the
  ``port:N``, ``prod:DEBUG`` and ``prod:.env`` rows and the ``run_doctor(port=, prod=)``
  parameters. ``uxdom build`` runs the pure-dom doctor and no longer prints a
  ``prod:DEBUG-note`` step. Use ``uxcompose doctor --prod [--port N]`` (ux-compose #128),
  which checks the channel secret, ``DEBUG``, ``.env``, dependencies, ``requirements.txt``
  and the port. Lock: ``test_doctor_product_rows_absent.py``.
