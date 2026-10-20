- **Fix: a reference at the end of an HTML string is kept (F-04).**
  ``Fragment("AT&T")`` rendered ``AT``: the tokenizer never closed the parser,
  so a trailing ``&T`` / ``&copy`` / ``&#60`` was dropped. It is now finished
  like a browser does (``AT&amp;T``, ``©``, ``&#60;``) on every Python 3.14
  patch release, including 3.14.0, whose ``HTMLParser.close`` drops the ``&``.
