- **`uxdom doctor` has no scaffold rows (ADR 0003 rules 3 and 4).** The ``scaffold`` and
  ``product-scaffold`` rows are gone, and a ``.ux_dom-scaffold.json`` marker no longer marks
  a project root (``app/main.py`` + ``app/settings.py`` still does). Nothing had written the
  marker since ``ux_dom.cli.scaffold`` was deleted, and ``product-scaffold`` was a constant
  pointer row. Scaffolding is ``uxcompose create-app``. Lock:
  ``test_doctor_product_rows_absent.py``.
