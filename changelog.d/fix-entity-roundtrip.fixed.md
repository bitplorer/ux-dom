- **Fix: a reference at the end of an HTML string is kept (F-04).**
  ``Fragment("AT&T")`` rendered ``AT``. The tokenizer never closed the parser,
  so a trailing ``&T``, ``&copy`` or ``&#60`` was dropped. It now ends the way a
  browser ends it (``AT&amp;T``, ``©``, ``&#60;``). An unfinished numeric
  reference ends at the first character that cannot continue it, and the rest
  is parsed as HTML through the sanitizer. ``a&#62b<img onerror=…>`` gives
  ``a&#62;b<img src="x">``. ``Char`` / ``Entity`` nodes only emit a well-formed
  reference. Anything else is escaped text. Unfinished numeric references are
  finished in one linear pass before parsing, so hostile input stays O(n). The
  output is the same on Python 3.14.0 and 3.14.1+.
