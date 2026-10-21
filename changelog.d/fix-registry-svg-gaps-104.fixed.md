- **Fix: the string sanitizer keeps ``linearGradient``, ``radialGradient``,
  ``clipPath`` and ``textPath`` (#104).** The tokenizer lowercases tag names,
  so these never matched the allowlist and were unwrapped. They are kept now
  and written with their SVG case (the HTML parser's SVG tag-name table),
  with ``gradientUnits``, ``gradientTransform``, ``spreadMethod``,
  ``clipPathUnits``, ``startOffset`` and ``clip-path``. Animation,
  ``foreignObject``, filters and ``image`` stay dropped or unwrapped.
