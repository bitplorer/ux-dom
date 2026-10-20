- **Fix: pretty render keeps adjacent inline elements together (#89).**
  ``str(div(b("a"), i("b")))`` put each on its own line, which a browser
  shows as ``a b``. Pretty render now knows the HTML spec's phrasing content:
  inline nodes next to each other, or at the inside edge of an inline element,
  render flat (``<b>x</b>``, ``<q>x</q>``); unknown and custom tags count as
  inline. Block-level children keep the indented layout, and text next to a
  block is indented again. An element the HTML parser moves (``<li>`` in
  ``<li>``, a block in ``<p>``, a ``<td>`` outside a table) renders flat.
  Pretty and flat now show the same text in Chromium for 1,200 random trees
  (102 differed before).
