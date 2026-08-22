# Copyright (c) 2023 ux-dom
#
# This software is released under the MIT License.
# https://opensource.org/licenses/MIT


"""FastAPI DirectoryRouter and streaming HTML route classes.

DirectoryRouter maps app/routes file paths to URLs; streaming helpers serialize
ux-dom trees for responses.

Path law (fixed, not flags):
* URL = filesystem only (folder + file stem). Class name never in path.
* route.py / index.py → folder prefix (or "/").

Page unit (default product path):
* Exports from ``__all__`` when present (Python-native allow-list).
* Page type = class whose name matches the module stem (cart.py → Cart).
* Ambiguous page picks fail closed (no silent guess).
* GET: explicit ``get`` method if present, else serve page unit via render.
* Other HTTP verbs only when explicit methods exist (advanced opt-in).

Generic hooks (optional, no host-specific types):
* resolve_unit(cls, path, name) → instance or None (None → cls())
  Used only for the synthetic page GET (when no explicit ``get`` exists).
  Explicit get/post/put/... methods on the class are used as-is and do
  not go through resolve_unit. Hosts typically key instances by
  ``cls.id`` or ``cls.__name__.lower()`` (soft contract).
* accept_symbol(name, obj, module) → bool
  Filter during discovery / page-unit selection. Exceptions → error.
* on_route(record) → None
  Called after a route is accepted. Exceptions → error when fail_closed.
"""
__all__ = ["HTMLRoute", "StreamingRoute", "DirectoryRouter", "RouterHooks", "DirectoryRouterError", "ResolveUnit", "AcceptSymbol", "OnRoute"]


import importlib
import logging
import re
import sys
from ux_dom import diagnostics as _ux_dom_diag
from collections import defaultdict
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Protocol, Sequence, Set, Type, Union, runtime_checkable

from fastapi import params, routing
from fastapi.datastructures import Default
from fastapi.utils import generate_unique_id
from starlette.responses import JSONResponse, Response
from starlette.routing import BaseRoute
from starlette.types import ASGIApp, Lifespan

from ux_dom.response.starlette import html_response, streaming_response

logger = logging.getLogger("ux_dom.routing")

_HTTP_VERBS = ("get", "post", "put", "patch", "delete", "head", "options")


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


class DirectoryRouterError(RuntimeError):
    """Fail-closed routing errors (ambiguous page, invalid export, etc.)."""


class RouterHooks:
    """Generic extension sockets for DirectoryRouter.

    All callables optional. Any host may pass hooks; ux-dom never imports
    host-specific types. With hooks=None, the synthetic page GET uses ``cls()``.

    resolve_unit is used only for the synthetic page GET (when the class has
    no explicit ``get``). Explicit HTTP methods declared on the class are
    used as-is and do not go through resolve_unit.

    Hosts that supply resolve_unit typically key live instances by
    ``getattr(cls, "id", None) or cls.__name__.lower()`` (soft contract).
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


def _module_exports(route_file: Any) -> list:
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


def _is_renderable_unit(klass: type) -> bool:
    return any(
        callable(getattr(klass, n, None))
        for n in ("render", "__render__", "__async_render__")
    )


def _pick_page_type(
    route_file: Any,
    exported: list,
    file_stem: str,
    *,
    accept_symbol: Optional[Callable[..., bool]] = None,
    fail_closed: bool = True,
):
    """Page unit = renderable class in exports whose name matches module stem."""
    mod_name = getattr(route_file, "__name__", "")
    stem = file_stem.lower()
    matches = []
    for name in exported:
        obj = getattr(route_file, name, None)
        if not isinstance(obj, type):
            continue
        if accept_symbol is not None:
            try:
                if not accept_symbol(name, obj, route_file):
                    continue
            except Exception as exc:
                raise DirectoryRouterError(
                    f"accept_symbol failed for {name!r}: {exc}"
                ) from exc
        if not hasattr(route_file, "__all__"):
            if getattr(obj, "__module__", None) not in (mod_name, file_stem):
                continue
        if not _is_renderable_unit(obj):
            continue
        if obj.__name__.lower() == stem:
            matches.append(obj)
    if len(matches) > 1:
        names = [m.__name__ for m in matches]
        msg = (
            f"ambiguous page unit for stem {file_stem!r}: {names}. "
            "Exactly one class name must match the file stem."
        )
        if fail_closed:
            raise DirectoryRouterError(msg)
        logger.error("%s", msg)
        return None
    if len(matches) == 1:
        return matches[0]
    return None


def _explicit_http_handlers(klass: type) -> dict:
    """Advanced opt-in: real HTTP handlers declared on the class."""
    found = {}
    for verb in _HTTP_VERBS:
        if verb in getattr(klass, "__dict__", {}):
            attr = klass.__dict__[verb]
            if staticmethod is not None and isinstance(attr, staticmethod):
                attr = attr.__func__
            if classmethod is not None and isinstance(attr, classmethod):
                attr = attr.__func__
            if callable(attr):
                found[verb] = getattr(klass, verb)
    return found


def _page_get_endpoint(
    klass: type,
    *,
    path: str,
    name: str,
    resolve_unit: Optional[ResolveUnit] = None,
):
    """Synthetic page GET: resolve_unit(klass, path, name) or Klass().

    Only used when the page class has no explicit ``get``. Explicit methods
    bypass this helper entirely.
    """

    def _endpoint():
        unit = None
        if resolve_unit is not None:
            try:
                unit = resolve_unit(klass, path, name)
            except Exception as exc:
                raise DirectoryRouterError(
                    f"resolve_unit failed for {klass.__name__} path={path}: {exc}"
                ) from exc
        if unit is None:
            unit = klass()
        return unit

    _endpoint.__name__ = f"{klass.__name__}_page_get"
    _endpoint.__doc__ = f"GET page unit {klass.__name__}"
    return _endpoint


def _import_route_module(module: str, file: Path):
    """Import a route file; fall back to file-location load for non-identifier dirs."""
    try:
        return importlib.import_module(module)
    except Exception:
        pass
    safe = (
        module.replace("/", ".").replace("\\", ".").replace("-", "_").replace(" ", "_")
    )
    safe_name = "_".join(safe.split("."))
    if not safe_name.isidentifier():
        safe_name = "ux_dom_route_" + str(abs(hash(str(file))))
    import importlib.util as _ilu

    spec = _ilu.spec_from_file_location(safe_name, file)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load route file {file}")
    mod = _ilu.module_from_spec(spec)
    sys.modules[safe_name] = mod
    spec.loader.exec_module(mod)
    return mod


def _api_route_kwargs(**kwargs: Any) -> dict:
    import inspect

    accepted = set(inspect.signature(routing.APIRoute.__init__).parameters)
    accepted.discard("self")
    return {k: v for k, v in kwargs.items() if k in accepted}


class HTMLRoute(routing.APIRoute):
    def __init__(self, path: str, endpoint: Callable[..., Any], **kwargs: Any) -> None:
        kwargs.setdefault("response_class", Default(JSONResponse))
        kwargs.setdefault("response_description", "Successful Response")
        kwargs.setdefault("response_model_by_alias", True)
        kwargs.setdefault("include_in_schema", True)
        kwargs.setdefault("generate_unique_id_function", Default(generate_unique_id))
        super().__init__(
            path=path,
            endpoint=html_response(endpoint),
            **_api_route_kwargs(**kwargs),
        )


class StreamingRoute(routing.APIRoute):
    def __init__(self, path: str, endpoint: Callable[..., Any], **kwargs: Any) -> None:
        kwargs.setdefault("response_class", Default(JSONResponse))
        kwargs.setdefault("response_description", "Successful Response")
        kwargs.setdefault("response_model_by_alias", True)
        kwargs.setdefault("include_in_schema", True)
        kwargs.setdefault("generate_unique_id_function", Default(generate_unique_id))
        super().__init__(
            path=path,
            endpoint=streaming_response(endpoint),
            **_api_route_kwargs(**kwargs),
        )


def _set_endpoint_name(endpoint: Any, name: str) -> Any:
    target = endpoint
    if hasattr(endpoint, "__func__"):
        target = endpoint.__func__
    try:
        setattr(target, "name", name)
        return endpoint
    except (AttributeError, TypeError):
        pass

    def _wrapped(*args, **kwargs):
        return endpoint(*args, **kwargs)

    _wrapped.name = name  # type: ignore[attr-defined]
    _wrapped.__name__ = getattr(endpoint, "__name__", name)
    _wrapped.__doc__ = getattr(endpoint, "__doc__", None)
    _wrapped.__wrapped__ = endpoint  # type: ignore[attr-defined]
    return _wrapped


def _default_get_endpoint(klass: type):
    return _page_get_endpoint(klass, path="", name=klass.__name__)


def _clean_url_prefix(relative_file_folder: str, base_directory: str) -> str:
    rel = relative_file_folder.replace("\\", "/").strip("/")
    base = base_directory.replace("\\", "/").strip("/")
    if rel == base:
        parts: List[str] = []
    elif rel.startswith(base + "/"):
        parts = rel[len(base) + 1 :].split("/")
    else:
        parts = rel.split("/") if rel else []
    cleaned: List[str] = []
    for part in parts:
        if not part or part.startswith("_") or part == ".":
            continue
        if part == "..":
            if not cleaned:
                return ""
            cleaned.pop()
            continue
        cleaned.append(part)
    if not cleaned:
        return ""
    return "/" + "/".join(cleaned)


def _to_fastapi_path_params(prefix: str) -> str:
    if not prefix:
        return prefix
    segs = []
    for seg in prefix.split("/"):
        if not seg:
            continue
        if len(seg) >= 2 and seg[0] == "[" and seg[-1] == "]":
            inner = seg[1:-1]
            if inner.startswith("..."):
                segs.append(seg)
            else:
                segs.append("{" + inner + "}")
        else:
            segs.append(seg)
    return ("/" + "/".join(segs)) if segs else ""


class DirectoryRouter(routing.APIRouter):
    _METHODS = list(_HTTP_VERBS)

    def __init__(
        self,
        base_directory: str = "app",
        route_file_name: str = "route",
        *,
        package_dir: Optional[Union[str, Path]] = None,
        prefix: str = "",
        tags: Optional[List[Union[str, Enum]]] = None,
        dependencies: Optional[Sequence[params.Depends]] = None,
        default_response_class: Type[Response] = Default(JSONResponse),
        responses: Optional[Dict[Union[int, str], Dict[str, Any]]] = None,
        callbacks: Optional[List[BaseRoute]] = None,
        routes: Optional[List[routing.BaseRoute]] = None,
        redirect_slashes: bool = True,
        default: Optional[ASGIApp] = None,
        dependency_overrides_provider: Optional[Any] = None,
        route_class: Type[routing.APIRoute] = StreamingRoute,
        on_startup: Optional[Sequence[Callable[[], Any]]] = None,
        on_shutdown: Optional[Sequence[Callable[[], Any]]] = None,
        lifespan: Optional[Lifespan[Any]] = None,
        deprecated: Optional[bool] = None,
        include_in_schema: bool = True,
        generate_unique_id_function: Callable[[routing.APIRoute], str] = Default(
            generate_unique_id
        ),
        **kwargs: Any,
    ):
        self._base_directory = base_directory
        self._route_file_name = route_file_name
        self._package_dir = Path(package_dir).resolve() if package_dir else None
        self._seen_routes: Set[tuple] = set()
        hooks = kwargs.pop("hooks", None)
        if hooks is not None and not isinstance(hooks, RouterHooks):
            raise TypeError("hooks must be a RouterHooks instance or None")
        self._hooks: RouterHooks = hooks or RouterHooks()
        self._on_unit = kwargs.pop("on_unit", None)
        self._fail_closed = bool(kwargs.pop("fail_closed", True))
        self._route_table: List[dict] = []
        super_kwargs = dict(
            prefix=prefix,
            tags=tags,
            dependencies=dependencies,
            default_response_class=default_response_class,
            responses=responses,
            callbacks=callbacks,
            routes=routes,
            redirect_slashes=redirect_slashes,
            default=default,
            dependency_overrides_provider=dependency_overrides_provider,
            route_class=route_class,
            on_startup=on_startup,
            on_shutdown=on_shutdown,
            lifespan=lifespan,
            deprecated=deprecated,
            include_in_schema=include_in_schema,
            generate_unique_id_function=generate_unique_id_function,
        )
        import inspect as _inspect

        accepted = set(_inspect.signature(routing.APIRouter.__init__).parameters)
        super_kwargs = {k: v for k, v in super_kwargs.items() if k in accepted}
        super().__init__(**super_kwargs)  # type: ignore[arg-type]
        self.build_router()

    def _resolve_package_root(self) -> Path:
        if self._package_dir is not None:
            return self._package_dir
        main = sys.modules.get("__main__")
        main_file = getattr(main, "__file__", None) if main else None
        if not main_file:
            raise RuntimeError(_ux_dom_diag.directory_router_no_package_dir())
        logger.warning(
            "DirectoryRouter using __main__.__file__ root %s; pass package_dir=",
            main_file,
        )
        return Path(main_file).resolve().parent

    def build_router(self):
        parent = self._resolve_package_root()
        _package_name = parent.name
        base = parent / self.base_directory
        if not base.exists():
            logger.warning("%s", _ux_dom_diag.directory_router_missing_base(str(base)))
            return

        for file in sorted(base.rglob("*.py")):
            if file.name == "__init__.py":
                continue
            if file.stem.startswith("_") or any(
                part.startswith("_") for part in file.relative_to(parent).parts[:-1]
            ):
                continue

            relative_file_folder = str(Path(file.parent).relative_to(parent)).replace(
                "\\", "/"
            )
            file_package_path = str(_package_name / Path(relative_file_folder)).replace(
                "\\", "/"
            )
            module = file_package_path.replace("/", ".") + "." + file.stem

            try:
                route_file = _import_route_module(module, file)
            except Exception:
                logger.exception("DirectoryRouter failed to import %s", module)
                continue

            if file.stem == self.route_file_name:
                # legacy route.py module with function verbs
                exported = _module_exports(route_file)
                route_methods = [
                    r
                    for r in exported
                    if r.lower() in self._METHODS
                    and callable(getattr(route_file, r, None))
                    and not isinstance(getattr(route_file, r, None), type)
                ]
                kind = "route_module"
                methods_payload: Any = route_methods
            else:
                exported = _module_exports(route_file)
                accept = self._hooks.accept_symbol
                page_cls = _pick_page_type(
                    route_file,
                    exported,
                    file.stem,
                    accept_symbol=accept,
                    fail_closed=self._fail_closed,
                )
                class_map: dict = defaultdict(dict)
                file_fns: dict = {}

                for name in exported:
                    obj = getattr(route_file, name, None)
                    if obj is None or isinstance(obj, type):
                        continue
                    if accept is not None:
                        try:
                            if not accept(name, obj, route_file):
                                continue
                        except Exception as exc:
                            raise DirectoryRouterError(
                                f"accept_symbol failed for {name!r}: {exc}"
                            ) from exc
                    if name.lower() in self._METHODS and callable(obj):
                        file_fns[name] = obj

                if page_cls is not None:
                    kname = page_cls.__name__
                    explicit = _explicit_http_handlers(page_cls)
                    for verb, fn in explicit.items():
                        class_map[kname][verb] = fn
                    if "get" not in class_map and _is_renderable_unit(page_cls):
                        class_map[kname]["get"] = _page_get_endpoint(
                            page_cls,
                            path="",
                            name=kname,
                            resolve_unit=self._hooks.resolve_unit,
                        )

                if class_map:
                    methods_payload = class_map
                    kind = "component"
                elif file_fns:
                    methods_payload = file_fns
                    kind = "file_fns"
                else:
                    kind = "empty"
                    methods_payload = {}

            if kind == "empty" or not methods_payload:
                continue

            tags = (
                ["default"]
                if relative_file_folder == self.base_directory
                else relative_file_folder.split("/")
            )
            prefix = _to_fastapi_path_params(
                _clean_url_prefix(relative_file_folder, self.base_directory)
            )
            _router = (
                routing.APIRouter(prefix=prefix, tags=tags)
                if prefix
                else routing.APIRouter(tags=tags)
            )
            _router.route_class = self.route_class

            if kind == "route_module":
                for method in methods_payload:
                    fn = getattr(route_file, method)
                    name = f"{module}:{method}"
                    fn = _set_endpoint_name(fn, name)
                    path = "/" if method.lower() in self._METHODS else f"/{method.lower()}"
                    methods = [method.lower()] if method.lower() in self._METHODS else ["get"]
                    self._add(_router, path, fn, name, methods)
            elif kind == "component":
                for klass_name, methods_map in methods_payload.items():
                    klass_obj = getattr(route_file, klass_name, None)
                    if callable(self._on_unit) and isinstance(klass_obj, type):
                        try:
                            self._on_unit(klass_obj, prefix, file)
                        except Exception as exc:
                            if self._fail_closed:
                                raise DirectoryRouterError(
                                    f"on_unit failed for {klass_name}: {exc}"
                                ) from exc
                            logger.exception("on_unit failed for %s", klass_name)
                    for _method, _method_attr in methods_map.items():
                        name = f"{module}.{klass_name}.{_method}"
                        mlow = _method.lower()
                        if mlow in self._METHODS:
                            if file.stem == self.route_file_name or file.stem == "index":
                                _route_ = "/"
                            elif not file.stem.startswith("_"):
                                _route_ = f"/{file.stem}"
                            else:
                                _route_ = "/"
                            methods = [mlow]
                        else:
                            if file.stem == self.route_file_name or file.stem == "index":
                                _route_ = f"/{mlow}"
                            elif not file.stem.startswith("_"):
                                _route_ = f"/{file.stem}/{mlow}"
                            else:
                                _route_ = f"/{mlow}"
                            methods = ["get"]
                        if (
                            mlow == "get"
                            and isinstance(klass_obj, type)
                            and getattr(_method_attr, "__name__", "").endswith("_page_get")
                        ):
                            _method_attr = _page_get_endpoint(
                                klass_obj,
                                path=(prefix or "") + _route_,
                                name=name,
                                resolve_unit=self._hooks.resolve_unit,
                            )
                        _method_attr = _set_endpoint_name(_method_attr, name)
                        self._add(_router, _route_, _method_attr, name, methods)
            elif kind == "file_fns":
                for fn_name, fn in methods_payload.items():
                    name = f"{module}.{fn_name}"
                    fn = _set_endpoint_name(fn, name)
                    mlow = fn_name.lower()
                    if mlow in self._METHODS:
                        path = f"/{file.stem}" if not file.stem.startswith("_") else "/"
                        methods = [mlow]
                    else:
                        path = (
                            f"/{file.stem}/{mlow}"
                            if not file.stem.startswith("_")
                            else f"/{mlow}"
                        )
                        methods = ["get"]
                    self._add(_router, path, fn, name, methods)

            self.include_router(_router)

        self._prioritize_static_routes()

    def _prioritize_static_routes(self) -> None:
        def split(routes):
            static, dynamic = [], []
            for route in routes:
                path = getattr(route, "path", "") or ""
                (dynamic if "{" in path else static).append(route)
            return static + dynamic

        self.routes[:] = split(list(self.routes))
        for route in list(self.routes):
            sub = getattr(route, "app", None) or getattr(route, "router", None)
            if sub is not None and hasattr(sub, "routes") and isinstance(sub.routes, list):
                try:
                    sub.routes[:] = split(list(sub.routes))
                except Exception:
                    pass

    def _add(self, router, path, endpoint, name, methods):
        key = (router.prefix + path, tuple(sorted(methods)))
        if key in self._seen_routes:
            if self._fail_closed:
                raise DirectoryRouterError(
                    f"duplicate route {methods} {key[0]} name={name}"
                )
            logger.warning(
                "DirectoryRouter duplicate route skipped: %s %s name=%s",
                methods,
                key[0],
                name,
            )
            return
        self._seen_routes.add(key)
        record = {
            "method": list(methods),
            "path": (router.prefix or "") + path,
            "name": name,
        }
        self._route_table.append(record)
        if self._hooks.on_route is not None:
            try:
                self._hooks.on_route(record)
            except Exception as exc:
                if self._fail_closed:
                    raise DirectoryRouterError(f"on_route failed for {record}: {exc}") from exc
                logger.exception("on_route failed for %s", record)
        router.add_api_route(
            path,
            endpoint,
            name=name,
            methods=methods,
            description=getattr(endpoint, "__doc__", None),
        )

    @property
    def route_table(self) -> List[dict]:
        """Deterministic list of registered routes (CI / doctor)."""
        return list(self._route_table)

    def _find_braces_or_brackets(self, string):
        pattern = re.compile(r"\{[^}]*\}|\[[^\]]*\]")
        return re.findall(pattern=pattern, string=string)

    @property
    def base_directory(self):
        return self._base_directory

    @base_directory.setter
    def base_directory(self, value):
        self._base_directory = value

    @property
    def route_file_name(self):
        return self._route_file_name
