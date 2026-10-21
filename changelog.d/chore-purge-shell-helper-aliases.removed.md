- **One name per shell helper (ADR 0004).** Removed ``Document.plugin_head_body()`` (use
  ``Document.runtime_tags()``), ``App.runtime_tags()`` (use ``App.shell_fragments()``),
  ``App.plugins()`` (use ``App.use()``), ``ux_dom.plugins.runtime_tags`` (use
  ``shell_fragments``), ``CspNonce`` (use ``Csp``) and ``shell_fragments_nonced`` (use
  ``shell_fragments``, which already stamps the nonce). The ``App.fastapi()`` tombstone and
  ``ProductHostMoved`` are gone: ``App.build()`` without ``asgi=`` raises ``TypeError``.
  Lock: ``test_shell_helper_aliases_absent.py``.
