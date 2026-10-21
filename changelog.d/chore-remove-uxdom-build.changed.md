- **`uxdom doctor` detects a pure-dom project by ``app/main.py`` alone (#106).**
  ``app/settings.py`` (product-layout residue, ADR 0003) is no longer required, so a tree
  with ``app/main.py`` now gets the project rows. The always-green ``app/main.py`` row is
  gone, since detection already proves the file exists. Doctor reads the project files and
  never imports the app. Lock: ``test_doctor_project_detection.py``.
