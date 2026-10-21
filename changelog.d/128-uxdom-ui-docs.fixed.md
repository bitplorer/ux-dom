- **Docs: ``uxdom ui`` lists the UI kit (#128).** ``docs/reference/UI.md``,
  ``docs/guides/SNIPPETS.md`` and the ``ux_dom.ui`` docstring said ``uxdom ui list``,
  which exits 2. A test now parses every ``uxdom`` line in a docs code block or a
  ``src`` docstring against the CLI.
