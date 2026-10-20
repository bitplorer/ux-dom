- **Security: `style` / `script` inside `<svg>` / `<math>` cannot inject markup.**
  In foreign content the HTML parser reads their body as markup, so
  `svg(style("<img src=x onerror=alert(1)>"))` ran. There the body is now one
  CDATA section (a `]]>` inside is split), so SVG CSS and JS run verbatim; an
  author's own outer `<![CDATA[ … ]]>` is unwrapped first. Below
  `foreignObject`, `desc`, `title`, an HTML `annotation-xml` and the MathML
  text elements (`mi`, `mo`, `mn`, `ms`, `mtext`), the raw text rules apply
  again. A `raw()` / `Markup` string that opens `<svg>` is author trust (#83).
