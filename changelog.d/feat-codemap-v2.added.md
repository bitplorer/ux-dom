- **Code map v2.** ``scripts/codemap.py`` is now repo-agnostic and config-driven
  (``[tool.codemap]`` in ``pyproject.toml``), so every ux-* / cek repo can vendor
  the same file. ``index.json`` records the generator's version and sha256. Module
  shards add symbols (signatures, first docstring line, decorators), external
  imports by distribution, the module docstring and features. The index adds
  entry points, a layer graph with ``layer_rules`` and ``layer_violations``, the
  curated ``docs/internals/features.toml`` and ``docs/internals/domain.toml``
  (domain charter: owned concepts, non-goals, ``depends_on``), coupling metrics,
  and doc claims (docs-ahead / code-ahead findings, with per-doc ``claims/``
  shards). ``--check`` also fails on broken feature, charter or narrative
  references, layer violations, unlisted cycles, and undeclared or private
  foreign imports. ``--feature ID`` prints one feature. See
  ``docs/internals/CODEMAP.md``.
