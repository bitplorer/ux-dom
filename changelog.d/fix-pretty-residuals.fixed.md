- **Fix: pretty render keeps the displayed text of option, ruby and moved
  elements (#94).** An ``<option>`` shows its label, which joins its text with
  one space per whitespace run, so ``option(dd(header("x"), "a'b"))`` showed
  ``x a'b`` pretty. ``<option>`` and ``<ruby>`` (which lays out everything in it
  inline) now render their body flat. The parser-moved list follows the "in
  body" rules: ``<dialog>`` closes a ``<p>``, ``<nobr>`` closes an open
  ``<nobr>``, a table part in a cell closes the cell, ``<html>`` / ``<head>`` /
  ``<body>`` below the top of the document are dropped, and a void element's
  children follow it. ``<dialog>`` counts as inline (hidden until open, then
  out of the flow). Pretty and flat now show the same text in Chromium for
  3 × 1,800 random trees (151 differed before).
