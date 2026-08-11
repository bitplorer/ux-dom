# Concurrency (internal behaviour)

### Brand lines

| Layer | Name |
|-------|------|
| **PyPI / pip** | `ux-dom` |
| **Import** | `ux_dom` |
| **CLI** | **`uxdom`** |

## For application developers

**You do not configure parallel or concurrency.**

Write normal code:

```python
html = root.__render__(pretty=False)
# or stream / Document / routes as usual
```

The library already:

* Locks the **same tree** so mutation + render never tear under threads
* Keeps **independent trees** free to run together
* Uses sequential vs parallel paths **internally** with safe defaults
* Matches sync and async HTML for frozen trees

There is nothing to opt into for day-1 DX.

## For maintainers / tests only

Advanced knobs live under `ux_dom.concurrency` (`configure_concurrency`, env
`UX_DOM_*`) and are **not** part of the product surface for apps.

### Profiling (p95 + flamegraphs)

```bash
python scripts/profile_p95.py
# → reports/p95/report.html
# → reports/p95/latency.json
# → reports/p95/profile.speedscope.json  (open in https://www.speedscope.app)
```

Tests: `tests/04_production/test_p95_profiling.py`.
