"""F-08: build_parallel inside with-tag must attach children."""

from __future__ import annotations

from ux_dom.concurrency import build_parallel
from ux_dom.dom import div, span


def test_one_and_many_attach_under_with():
    with div() as root1:
        build_parallel(lambda i: span(str(i)), [1])
    with div() as root2:
        build_parallel(lambda i: span(str(i)), [1, 2])
    assert len(root1.children) == 1
    assert len(root2.children) == 2


def test_explicit_parallel_false_still_works():
    with div() as root:
        build_parallel(lambda i: span(str(i)), [1, 2, 3], parallel=False)
    assert len(root.children) == 3
