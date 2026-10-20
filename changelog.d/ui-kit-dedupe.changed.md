- **Refactor: UI kit duplication (D6, D7, D9).** Dialog / Sheet / Command share
  one overlay root and panel, Carousel / Pagination / Tabs share Channel action
  stamping and nav-button chrome, Textarea uses ``field_classes(height=)``, and
  Alert / Toast read one ``status`` tone table. Drift settled: Sheet's panel gains
  ``aria-labelledby`` / ``tabindex="-1"`` (body ``mt-3`` → ``mt-2``); Carousel nav
  buttons take Pagination's ``target["sm"]`` chrome; Toast info/success and
  Alert destructive tones align (``bg-stone-900/90``, ``emerald-500/40``,
  ``red-500/40 text-red-100``). The Dialog / Sheet title id is now
  ``<root id>-title`` (default ``overlay-title``, was ``dialog-title``), so two
  open overlays with distinct ids no longer share an id.
- **Fix: ``uxdom add ui`` onto an older kit copy.** When a kept ``tokens.py`` (or
  other kit file) lacks a name or keyword the new component uses, ``copy_component``
  raises ``UiCopyError`` naming them and pointing to ``--force``, instead of
  writing a module that fails to import.
