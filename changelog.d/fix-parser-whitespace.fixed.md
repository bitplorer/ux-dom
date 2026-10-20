- **Fix: parsing an HTML string keeps its whitespace (#96).** ``defHTML``,
  ``Fragment(str)`` and every other string path dropped text with a newline
  at its edges, so ``<pre>\n  code</pre>`` lost its indent, a ``textarea``
  lost the newlines of its value and ``a\n<b>x</b>`` showed ``ax``. Text is
  now kept as written, CRLF and a lone CR become LF as in a browser, and
  ``listing`` is allowed like ``pre``. Pretty render of parsed HTML shows
  the whitespace text between blocks as blank lines.
