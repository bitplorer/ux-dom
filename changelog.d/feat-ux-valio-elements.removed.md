- **BREAKING: legacy `valio` and the `ux_dom.compat` PEP 649 shim removed.** `ux_dom.elements`
  now validates with `ux-valio`, pinned by commit SHA in `pyproject.toml`; `valio` and
  `typingx` are no longer dependencies, and `import ux_dom` no longer patches a third-party
  package. Element rendering is unchanged, except that `RadioInput(checked=False)` now
  renders unchecked (legacy valio replaced `False` with the `"checked"` default).
  Lock: `tests/07_resilience/test_f16_ux_valio_elements.py`.
