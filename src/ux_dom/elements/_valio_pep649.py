"""
Make third-party ``valio`` importable and correct on Python 3.14+ (PEP 649).

valio ≤0.1.0b6 assumes class ``__annotations__`` is eagerly stored in
``owner.__dict__``. On 3.14 that is false — annotations live behind
``__annotate_func__`` / ``__annotations_cache__``. The stock descriptor
hook::

    if "__annotations__" not in owner.__dict__:
        owner.__annotations__ = {}

wipes every annotation and breaks both valio's own hierarchy and consumer
dataclasses (e.g. ``CharInput`` fields).

Strategy
--------
1. Load ``valio.descriptor.descriptors`` first (without the package init).
2. **Replace** (not merely wrap) the annotation hooks with PEP 649-safe
   implementations so field collection keeps every annotated name.
3. Import the full package.
"""

from __future__ import annotations

import importlib
import importlib.util
import sys
import types
from pathlib import Path

_APPLIED = False


def _materialize_annotations(owner) -> dict:
    """Return a real annotations dict; never wipe PEP 649 deferred anns."""
    anns: dict = {}
    try:
        import inspect

        anns = dict(inspect.get_annotations(owner, eval_str=False) or {})
    except Exception:
        anns = {}
    if not anns:
        try:
            from annotationlib import Format, get_annotations  # type: ignore

            for fmt in (Format.VALUE, Format.FORWARDREF, Format.STRING):
                try:
                    got = dict(get_annotations(owner, format=fmt) or {})
                    if got:
                        anns = got
                        break
                except Exception:
                    continue
        except Exception:
            pass
    raw = getattr(owner, "__annotations__", None)
    if isinstance(raw, dict):
        for k, v in raw.items():
            anns.setdefault(k, v)

    existing = owner.__dict__.get("__annotations__")
    if anns:
        if not isinstance(existing, dict):
            try:
                owner.__annotations__ = dict(anns)
            except Exception:
                pass
        else:
            for k, v in anns.items():
                existing.setdefault(k, v)
    elif not isinstance(existing, dict):
        if not raw:
            try:
                owner.__annotations__ = {}
            except Exception:
                pass
    return dict(
        owner.__dict__.get("__annotations__")
        or getattr(owner, "__annotations__", None)
        or anns
        or {}
    )


def _install_safe_hooks(Property) -> None:
    """Replace Property annotation hooks with PEP 649-safe versions."""

    def _set_name(self, owner, name, logger):  # noqa: ANN001
        if self.errors is None:
            self.errors = []
        try:
            if self.name is None:
                self.name = name
                if logger:
                    logger.info(f"assigned: {owner.__name__}.{name}")
            elif name != self.name and self.annotation == _materialize_annotations(
                owner
            ).get(name, None):
                raise AttributeError(
                    f"{self.name} != {name}, attribute names did not match"
                )
        except Exception as name_err:
            if logger:
                logger.error(name_err)
            self.errors.append(name_err)
            raise name_err

    def _may_set_or_ensure_annotation_match(self, owner, name, logger):  # noqa: ANN001
        if self.errors is None:
            self.errors = []
        try:
            anns = _materialize_annotations(owner)
            if name in anns:
                if self.annotation is None:
                    self.annotation = anns[name]
                else:
                    owner_annotation = anns[name]
                    # Prefer class annotation over validator TypeVar soup.
                    if owner_annotation != self.annotation:
                        try:
                            from typingx import issubclassx

                            if not issubclassx(owner_annotation, self.annotation):
                                pass  # keep owner annotation as SoT
                        except Exception:
                            pass
                        self.annotation = owner_annotation
            else:
                if self.annotation:
                    anns = _materialize_annotations(owner)
                    if not isinstance(owner.__dict__.get("__annotations__"), dict):
                        owner.__annotations__ = dict(anns)
                    owner.__annotations__[name] = self.annotation
        except Exception as annotation_err:
            if logger:
                logger.error(annotation_err)
            self.errors.append(annotation_err)
            # Soft-fail: do not abort class creation on annotation bookkeeping.
            return

    def _set_docs(self, owner, name, logger):  # noqa: ANN001
        anns = _materialize_annotations(owner)
        owner_annotation = anns.get(name, getattr(self, "annotation", None))
        if self.errors is None:
            self.errors = []
        try:
            owner.__doc__ = owner.__doc__ or f"Class: {owner.__name__}"
            owner.__doc__ += (
                (
                    f"\n\t:param {owner_annotation} {str(self)}: {self.doc}"
                    if self.annotation
                    else f"\n\t:param {str(self)}: {self.doc}"
                )
                if self.doc is not None
                else (
                    f"\n\t:param {owner_annotation} {str(self)}:"
                    if self.annotation
                    else f"\n\t:param {str(self)}:"
                )
            )
        except Exception as doc_err:
            if logger:
                logger.error(doc_err)
            self.errors.append(doc_err)
            return

    Property._set_name = _set_name  # type: ignore[method-assign]
    Property._may_set_or_ensure_annotation_match = (  # type: ignore[method-assign]
        _may_set_or_ensure_annotation_match
    )
    Property._set_docs = _set_docs  # type: ignore[method-assign]


def _load(fullname: str, path: Path, *, is_pkg: bool = False):
    spec = importlib.util.spec_from_file_location(
        fullname,
        str(path),
        submodule_search_locations=[str(path.parent)] if is_pkg else None,
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {fullname} from {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[fullname] = mod
    spec.loader.exec_module(mod)
    return mod


def ensure_valio_pep649_compat() -> None:
    """Idempotent. Call before any ``import valio`` on Python 3.14+."""
    global _APPLIED
    if _APPLIED:
        return
    if sys.version_info < (3, 14):
        _APPLIED = True
        return
    if "valio.validator.validators" in sys.modules and hasattr(
        sys.modules.get("valio"), "Validator"
    ):
        # Already imported — still install safe hooks if Property is present.
        try:
            from valio.descriptor.descriptors import Property

            _install_safe_hooks(Property)
        except Exception:
            pass
        _APPLIED = True
        return

    try:
        from importlib.metadata import distribution

        dist = distribution("valio")
    except Exception:
        _APPLIED = True
        return

    desc_path = None
    root = None
    for f in dist.files or []:
        s = str(f).replace("\\", "/")
        if s.endswith("descriptor/descriptors.py"):
            desc_path = Path(f.locate())
            root = desc_path.parent.parent  # .../valio
            break
    if not desc_path or not desc_path.is_file() or root is None:
        _APPLIED = True
        return

    # Drop any incomplete valio modules from a prior failed import
    for k in list(sys.modules):
        if k == "valio" or k.startswith("valio."):
            del sys.modules[k]

    def pkg_shell(name: str, path: Path) -> types.ModuleType:
        m = types.ModuleType(name)
        m.__path__ = [str(path)]  # type: ignore[attr-defined]
        m.__package__ = name
        sys.modules[name] = m
        return m

    pkg_shell("valio", root)
    pkg_shell("valio.error", root / "error")
    pkg_shell("valio.logger", root / "logger")
    pkg_shell("valio.descriptor", root / "descriptor")

    _load("valio.error.errors", root / "error" / "errors.py")
    _load("valio.logger.loggers", root / "logger" / "loggers.py")
    desc = _load("valio.descriptor.descriptors", root / "descriptor" / "descriptors.py")
    if hasattr(desc, "Property"):
        _install_safe_hooks(desc.Property)

    # Keep patched descriptors; replace package shells with real inits
    keep = {
        "valio.descriptor.descriptors": sys.modules["valio.descriptor.descriptors"],
        "valio.error.errors": sys.modules["valio.error.errors"],
        "valio.logger.loggers": sys.modules["valio.logger.loggers"],
    }
    for k in list(sys.modules):
        if k == "valio" or k.startswith("valio."):
            if k not in keep:
                del sys.modules[k]
    sys.modules.update(keep)

    importlib.invalidate_caches()
    valio = importlib.import_module("valio")
    if not hasattr(valio, "Validator"):
        if not getattr(valio, "__file__", None):
            valio = _load("valio", root / "__init__.py", is_pkg=True)
    _APPLIED = True


__all__ = ["ensure_valio_pep649_compat"]
