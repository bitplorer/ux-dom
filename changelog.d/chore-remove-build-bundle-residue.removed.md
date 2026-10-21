- **BREAKING: `uxdom build` writes no runnable bundle (ADR 0003 rules 3 and 4).** The
  ``--package`` / ``-p``, ``--archive``, ``--out`` and ``--name`` options are gone, with
  ``run_build(package=, archive=, out_dir=, package_name=)``, ``BuildReport.package_path``
  and ``static_assets.write_runnable_package`` / ``collect_package_files``. This also
  removes the data loss in #101: the bundle went to ``<out>/<project name>``, so
  ``uxdom build --package --out ..`` cleared the project. Use
  ``uxcompose build --package [--archive]`` (ux-compose #130), which refuses an
  ``--out`` that is or contains the app. Lock: ``test_build_bundle_absent.py``.
