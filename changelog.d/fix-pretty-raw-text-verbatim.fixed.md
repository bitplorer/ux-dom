- **Fix: pretty render keeps raw text and preformatted bodies verbatim (#88).**
  ``str(div(listing("a\n  b")))`` indented the body, so the browser showed
  ``"    a\n      b\n  "``; the same held for ``xmp``, ``plaintext`` and a
  ``pre`` written by a class with another case (``PRE``). The body of every
  element the parser reads as raw text, RCDATA, RAWTEXT, PLAINTEXT or
  preformatted text (``script``, ``style``, ``textarea``, ``title``, ``xmp``,
  ``iframe``, ``noembed``, ``noframes``, ``noscript``, ``plaintext``,
  ``pre``, ``listing``), matched by tag name in any case, is now written as
  the flat render writes it. Only the layout around it is pretty.
