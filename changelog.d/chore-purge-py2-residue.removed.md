- **Python 2 residue and private tag aliases (ADR 0004).** The DOM layer no longer
  defines ``basestring`` / ``unicode`` / ``unichr`` compat names or the ``__unicode__`` /
  ``__nonzero__`` dunders (use ``str`` / ``chr`` / ``__str__`` / ``__bool__``). Removed the
  htmltags ``_time`` / ``_del`` / ``_object`` / ``_map`` / ``_input`` aliases (use
  ``time_`` / ``del_`` / ``object_`` / ``map_`` / ``input_``) and ``ux_dom.dom.src.main``
  (import ``ux_dom.dom.src.ext``). Lock: ``test_py2_residue_absent.py``.
