- **`figcaption` and `sub` are exported (#126).** Both classes were defined but
  missing from `htmltags.__all__`, so `from ux_dom.dom import sub` raised
  `ImportError`. A test keeps `__all__` equal to the defined tag classes.
