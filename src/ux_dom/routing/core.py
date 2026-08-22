"""Pure routing core — path law, page unit, hooks, route records.

No FastAPI / Starlette imports. Host adapters (e.g. ``routing.fastapi``)
materialize framework routes from :class:`DirectoryRoutes`.

Locked model:
  - URL path = filesystem relative to base (class name never in path)
  - Page unit = renderable class whose name matches the module stem
  - fail_closed on ambiguity / duplicates
  - RouterHooks.resolve_unit only for synthetic page GET
"""
from __future__ import annotations

import importlib.util
import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional, Protocol, runtime_checkable

logger = logging.getLogger("ux_dom.routing.core")

__all__ = [
    "DirectoryRouterError",
    "RouterHooks",
    "ResolveUnit",
    "AcceptSymbol",
    "OnRoute",
    "DirectoryRoutes",
    "RouteRecord",
    "pick_page_type",
    "module_exports",
]


class DirectoryRouterError(RuntimeError):
    """Fail-closed routing errors (ambiguous page, invalid export, etc.)."""


@runtime_checkable
class ResolveUnit(Protocol):
    """(cls, path, name) → instance | None. None → caller falls back to cls()."""

    def __call__(self, cls: type, path: str, name: str) -> Any: ...


@runtime_checkable
class AcceptSymbol(Protocol):
    """(name, obj, module) → bool. False skips the symbol; raise → error."""

    def __call__(self, name: str, obj: Any, module: Any) -> bool: ...


@runtime_checkable
class OnRoute(Protocol):
    """(record) → None. record = {method, path, name}. Raise → error if fail_closed."""

    def __call__(self, record: dict) -> None: ...


class RouterHooks:
    """Generic extension sockets — host-agnostic.

    resolve_unit is used only for the synthetic page GET (when the class has
    no explicit ``get``). Explicit HTTP methods bypass resolve_unit.
    """

    __slots__ = ("resolve_unit", "accept_symbol", "on_route")

    def __init__(
        self,
        resolve_unit: Optional[ResolveUnit] = None,
        accept_symbol: Optional[AcceptSymbol] = None,
        on_route: Optional[OnRoute] = None,
    ):
        self.resolve_unit = resolve_unit
        self.accept_symbol = accept_symbol
        self.on_route = on_route


def module_exports(route_file: Any) -> list:
    if hasattr(route_file, "__all__"):
        return [str(x) for x in list(route_file.__all__)]
    mod_name = getattr(route_file, "__name__", "")
    names = []
    for r in dir(route_file):
        if r.startswith("_"):
            continue
        obj = getattr(route_file, r, None)
        if isinstance(obj, type) and getattr(obj, "__module__", None) == mod_name:
            names.append(r)
        elif callable(obj) and not isinstance(obj, type):
            if getattr(obj, "__module__", None) == mod_name:
                names.append(r)
    return names


def is_renderable_unit(klass: type) -> bool:
    return any(
        callable(getattr(klass, n, None))
        for n in ("render", "__render__", "__async_render__")
    )


def pick_page_type(
    route_file: Any,
    exported: list,
    file_stem: str,
    *,
    accept_symbol: Optional[Callable[..., bool]] = None,
    fail_closed: bool = True,
):
    """Select the page unit: renderable class whose name matches the file stem."""
    mod_name = getattr(route_file, "__name__", "")
    stem = file_stem.lower()
    matches = []
    for name in exported:
        obj = getattr(route_file, name, None)
        if not isinstance(obj, type):
            continue
        if getattr(obj, "__module__", None) != mod_name:
            continue
        if accept_symbol is not None:
            try:
                if not accept_symbol(name, obj, route_file):
                    continue
            except Exception:
                continue
        if not is_renderable_unit(obj):
            continue
        if name.lower() == stem or getattr(obj, "__name__", "").lower() == stem:
            matches.append(obj)
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        msg = (
            f"Ambiguous page unit in {getattr(route_file, '__name__', '?')}: "
            f"multiple renderable classes match stem {file_stem!r}: "
            f"{[m.__name__ for m in matches]}"
        )
        if fail_closed:
            raise DirectoryRouterError(msg)
        logger.warning("%s", msg)
        return None
    return None


def import_route_module(module: str, file: Path) -> Any:
    if module in sys.modules:
        return sys.modules[module]
    spec = importlib.util.spec_from_file_location(module, file)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load {file}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[module] = mod
    spec.loader.exec_module(mod)
    return mod


@dataclass
class RouteRecord:
    """Pure route record — host adapters bind callables to framework routes."""

    method: str
    path: str
    name: str
    handler: Any = None
    page_cls: Any = None
    kind: str = "page"  # page | explicit | route_module


@dataclass
class DirectoryRoutes:
    """Discover page units under base_directory. No framework imports.

    Usage::

        core = DirectoryRoutes(package_dir, hooks=hooks)
        records = core.discover()
        # adapter.mount(core, asgi_app)
    """

    package_dir: Path
    base_directory: str = "routes"
    hooks: Optional[RouterHooks] = None
    fail_closed: bool = True
    methods: tuple = ("get", "post", "put", "patch", "delete")
    records: list = field(default_factory=list)

    def discover(self) -> list:
        parent = Path(self.package_dir).resolve()
        base = parent / self.base_directory
        self.records = []
        if not base.exists():
            logger.warning("DirectoryRoutes missing base %s", base)
            return self.records

        package_name = parent.name
        hooks = self.hooks or RouterHooks()

        for file in sorted(base.rglob("*.py")):
            if file.name == "__init__.py" or file.stem.startswith("_"):
                continue
            if any(part.startswith("_") for part in file.relative_to(parent).parts[:-1]):
                continue

            rel_folder = str(Path(file.parent).relative_to(parent)).replace("\\", "/")
            file_package_path = f"{package_name}/{rel_folder}".replace("\\", "/")
            module = file_package_path.replace("/", ".") + "." + file.stem
            try:
                route_file = import_route_module(module, file)
            except Exception:
                logger.exception("DirectoryRoutes failed to import %s", module)
                continue

            try:
                rel = file.relative_to(base).with_suffix("")
            except ValueError:
                continue
            parts = list(rel.parts)
            path = "/" + "/".join(parts)

            exported = module_exports(route_file)
            page_cls = pick_page_type(
                route_file,
                exported,
                file.stem,
                accept_symbol=hooks.accept_symbol,
                fail_closed=self.fail_closed,
            )
            if page_cls is None:
                continue

            explicit = []
            for m in self.methods:
                fn = getattr(page_cls, m, None)
                if callable(fn) and not isinstance(fn, type):
                    explicit.append(m)

            if explicit:
                for m in explicit:
                    rec = RouteRecord(
                        method=m.upper(),
                        path=path,
                        name=f"{page_cls.__name__}.{m}",
                        handler=getattr(page_cls, m),
                        page_cls=page_cls,
                        kind="explicit",
                    )
                    self._emit(rec, hooks)
            else:
                rec = RouteRecord(
                    method="GET",
                    path=path,
                    name=page_cls.__name__,
                    handler=None,
                    page_cls=page_cls,
                    kind="page",
                )
                self._emit(rec, hooks)

        return self.records

    def _emit(self, rec: RouteRecord, hooks: RouterHooks) -> None:
        payload = {
            "method": rec.method,
            "path": rec.path,
            "name": rec.name,
            "kind": rec.kind,
            "page_cls": rec.page_cls,
        }
        if hooks.on_route is not None:
            try:
                hooks.on_route(payload)
            except Exception as exc:
                if self.fail_closed:
                    raise DirectoryRouterError(str(exc)) from exc
        self.records.append(rec)

    def route_table(self) -> list:
        return [
            {"method": r.method, "path": r.path, "name": r.name, "kind": r.kind}
            for r in self.records
        ]
