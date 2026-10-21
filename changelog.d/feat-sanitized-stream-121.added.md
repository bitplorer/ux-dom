- **``ux_dom.response.sanitize_html`` and ``sanitize_html_stream`` (#121).**
  Public API for untrusted HTML strings, whole or as sync / async ``str``
  chunks, with the one string sanitizer (``defHTML``, ADR 0002).
  ``sanitize_html(s)`` is the ``defHTML(s)`` nodes rendered, with nothing added
  (no trailing newline). A stream is cut only where the tokenizer has no open
  element, tag, comment, raw text or reference, so its output is
  byte-identical to the whole string wherever the chunks split. Time is linear
  and the text held between two cuts is at most ``max_chars``
  (``MAX_BUFFER_CHARS``, 1 MiB characters); past that it raises
  ``HtmlStreamOverflow`` and emits nothing of the held text. A ``Markup``
  chunk stays verbatim. Lock: ``test_sanitized_stream.py`` and the Chromium
  oracle ``test_sanitized_stream_browser.py`` (0 executions over the #32 to
  #113 corpora, whole and chunked).
