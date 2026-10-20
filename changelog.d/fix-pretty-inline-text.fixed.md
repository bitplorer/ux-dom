- **Fix: pretty render keeps the displayed text of mixed content (#79).**
  ``str(Fragment("a&#39;b"))`` gave ``a\n\n&#39;\n\nb\n``, which a browser
  shows as ``a ' b``, and ``<p>AT&T x</p>`` showed as ``AT &T x``. A pretty
  newline next to text is a space in a browser. Text next to other inline
  nodes (references, ``<b>``, ``<a>``, …) now renders flat, so
  ``<p>hello <b>world</b>.</p>`` stays on one line.
