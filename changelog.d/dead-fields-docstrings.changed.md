- **Fix: ``profile.speedscope.json`` weights frames by self time.** Cumulative
  weights counted every callee again in each caller. Removed the never-read
  ``PackageStaticContribution.mount_package`` / ``mount_subdir`` fields and the
  unused ``static_from_package(mount_subdir=)`` keyword; corrected wrong
  docstrings (``uniqueid`` length, ``Htmx`` prefix, ``Slots`` ``shadowroot``,
  ``alpinejs.dataset`` example, ``Else`` / ``CSRFToken`` params).
