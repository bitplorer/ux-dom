- **Dead ``contextvars`` fallback in ``dom_tag`` (#128).** ``ContextVar`` is always
  imported, so the ``_WITH_STACK is None`` branches and ``dom_tag._render_stack`` never
  ran. Removed with ``_get_thread_context`` (no callers) and its optional ``greenlet``
  import; ``greenlet`` was never a dependency.
