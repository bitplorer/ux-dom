- **Fix: CSS rule values are raw text inside ``<style>``.** ``font_family="'Courier New'"``
  rendered as ``&#39;Courier New&#39;`` and the browser dropped the declaration.
  ``style`` still neutralizes ``</style`` (#127).
- **Fix: a leading LF in ``pre`` / ``listing`` / ``textarea`` survives.** The renderer
  writes one more LF before a body that starts with one, and the string parser drops
  the LF after the start tag as the browser does, so ``textarea("\nhello")`` keeps its
  value and a parse and render round-trip (#127).
