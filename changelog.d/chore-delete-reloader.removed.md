- **Reloader:** delete ``ux_dom.reloader`` (HMR residue). Product HMR is ``uxcompose serve``.
  Its only users of ``anyio`` and ``watchfiles`` went with it: ``anyio`` is no longer a
  direct dependency and ``watchfiles`` leaves the ``dev`` / ``fastapidev`` extras.
