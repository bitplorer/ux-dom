"""MRO parameter consistency for critical overrides (render / membership)."""

from __future__ import annotations

import importlib
import inspect
import unittest
import warnings
from pathlib import Path

CRITICAL = {
    "_render",
    "_render_children",
    "_walk_render_tokens",
    "get",
    "matches",
    "clean_attribute",
    "clean_pair",
    "_render_open_tag",
}


def _unwrap(a):
    if isinstance(a, (classmethod, staticmethod)):
        return a.__func__
    return a


def _compat(child_sig, parent_sig):
    problems = []
    c_has_var_kw = any(
        p.kind == inspect.Parameter.VAR_KEYWORD for p in child_sig.parameters.values()
    )
    for name, p in parent_sig.parameters.items():
        if name in ("self", "cls"):
            continue
        if p.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
            continue
        if name not in child_sig.parameters:
            if not c_has_var_kw:
                problems.append(f"missing `{name}`")
        else:
            c = child_sig.parameters[name]
            if (
                c.default is inspect.Parameter.empty
                and p.default is not inspect.Parameter.empty
            ):
                problems.append(f"`{name}` required but parent optional")
    return problems


class TestMroSignatures(unittest.TestCase):
    def test_critical_overrides_compatible(self):
        root = Path(__file__).resolve().parents[2] / "src" / "ux_dom"
        modules = []
        for path in root.rglob("*.py"):
            if "__pycache__" in str(path):
                continue
            rel = path.relative_to(root.parent)
            if rel.name == "__init__.py":
                name = ".".join(rel.parts[:-1])
            else:
                name = ".".join(rel.with_suffix("").parts)
            if name.startswith("ux_dom.cli") or name.startswith("ux_dom.examples"):
                continue
            modules.append(name)

        issues = []
        seen = set()
        for name in sorted(set(modules)):
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    mod = importlib.import_module(name)
            except Exception:
                continue
            for cls_name, cls in list(vars(mod).items()):
                if not isinstance(cls, type):
                    continue
                if not str(getattr(cls, "__module__", "")).startswith("ux_dom"):
                    continue
                if cls.__module__ != name or id(cls) in seen:
                    continue
                seen.add(id(cls))
                mro = [c for c in cls.__mro__[1:] if c is not object]
                for method, raw in list(cls.__dict__.items()):
                    if method not in CRITICAL:
                        continue
                    cfn = _unwrap(raw)
                    if not callable(cfn) or isinstance(cfn, type):
                        continue
                    parent = None
                    praw = None
                    for base in mro:
                        if method in base.__dict__:
                            parent = base
                            praw = base.__dict__[method]
                            break
                    if parent is None:
                        continue
                    pfn = _unwrap(praw)
                    if not callable(pfn) or isinstance(pfn, type):
                        continue
                    try:
                        cs = inspect.signature(cfn)
                        ps = inspect.signature(pfn)
                    except (TypeError, ValueError):
                        continue
                    for pr in _compat(cs, ps):
                        issues.append(
                            f"{name}.{cls_name}.{method} vs {parent.__name__}: {pr}"
                        )

        self.assertEqual(issues, [], msg="\n".join(issues))

    def test_render_overrides_accept_seen(self):
        from ux_dom.dom.src.dom_tag import dom_tag

        missing = []
        for cls in [
            dom_tag,
            __import__("ux_dom.dom.src.ext", fromlist=["Tags"]).Tags,
            __import__(
                "ux_dom.dom.src.component", fromlist=["ReactiveComponent"]
            ).ReactiveComponent,
            __import__(
                "ux_dom.dom.htmldocument", fromlist=["HtmlDocument"]
            ).HtmlDocument,
        ]:
            sig = inspect.signature(cls._render)
            if "_seen" not in sig.parameters:
                missing.append(f"{cls.__name__}{sig}")
        self.assertEqual(missing, [])


if __name__ == "__main__":
    unittest.main()
