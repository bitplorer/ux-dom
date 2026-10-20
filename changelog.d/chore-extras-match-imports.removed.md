- **Extras match imports (ADR 0003 rule 2).** ``ux-dom[fastapi]`` now installs only
  ``fastapi`` (it brings Starlette for ``ux_dom.response.starlette`` and
  ``install_safe_static``). The ``dev`` and
  ``fastapidev`` extras are gone, and ``uvicorn``, ``python-multipart`` and
  ``pytailwindcss`` are no longer ux-dom extras: install ``ux-compose`` for the ASGI server
  (``uxcompose serve``) and Tailwind compile (``uxcompose build``; pytailwindcss waiver,
  ux-compose #116 D3). ``uxdom doctor`` drops its ``dep:uvicorn`` row, which pointed at
  the old extra. Lock: ``test_extras_match_imports.py``.
