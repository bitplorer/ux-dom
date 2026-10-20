- **Refactor: ``uxdom build`` reports only checks that can fail.** The always-green
  ``assets-mount`` / ``css`` / ``css-artifacts`` steps are gone; ``SyncReport`` gains
  ``errors`` and ``ok`` reflects them, so a static-sync error fails the build;
  ``--package`` syncs once. The unused ``uxdom dashboard`` panel/asset registry
  (``Asset``, ``Panel``, ``register_panel``, …) is removed; output is unchanged.
