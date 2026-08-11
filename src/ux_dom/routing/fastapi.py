# Copyright (c) 2023 ux-dom
#
# This software is released under the MIT License.
# https://opensource.org/licenses/MIT


"""FastAPI DirectoryRouter and streaming HTML route classes.

DirectoryRouter maps app/routes file paths to URLs; streaming helpers serialize
ux-dom trees for responses.
"""
__all__ = ["HTMLRoute", "StreamingRoute", "DirectoryRouter"]


import importlib
import logging
import re
import sys
from ux_dom import diagnostics as _ux_dom_diag
from collections import defaultdict
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Set, Type, Union

from fastapi import params, routing
from fastapi.datastructures import Default
from fastapi.utils import generate_unique_id
from starlette.responses import JSONResponse, Response
from starlette.routing import BaseRoute
from starlette.types import ASGIApp, Lifespan

from ux_dom.response.starlette import html_response, streaming_response

logger = logging.getLogger("ux_dom.routing")


def _import_route_module(module: str, file: Path):
    """Import a route file; fall back to file-location load for non-identifier dirs.

    Folders like ``api.v1`` are valid URL segments but not valid Python package
    segments (``edgeapp.app.api.v1.route`` is mis-parsed as package ``api``).
    """
    try:
        return importlib.import_module(module)
    except Exception:
        # ModuleNotFoundError, or dotted folder segments, etc.
        pass
    # File-based import with a unique, valid module name
    safe = (
        module.replace("/", ".").replace("\\", ".").replace("-", "_").replace(" ", "_")
    )
    # Collapse dots inside path segments that came from dotted folder names:
    # edgeapp.app.api.v1.route → keep as synthetic name with underscores
    parts = safe.split(".")
    safe_name = "_".join(parts)
    if not safe_name.isidentifier():
        safe_name = "ux_dom_route_" + str(abs(hash(str(file))))
    import importlib.util as _ilu

    spec = _ilu.spec_from_file_location(safe_name, file)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load route file {file}")
    mod = _ilu.module_from_spec(spec)
    # Register so dataclasses / pickle / re-import behave
    sys.modules[safe_name] = mod
    spec.loader.exec_module(mod)
    return mod


def _api_route_kwargs(**kwargs: Any) -> dict:
    """Filter kwargs to those accepted by the installed FastAPI APIRoute.

    Prevents TypeError when FastAPI adds params (e.g. strict_content_type)
    that older hand-written StreamingRoute/HTMLRoute signatures omit.
    """
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
    """Attach a stable route name without crashing on bound methods.

    ``setattr(bound_method, "name", ...)`` raises AttributeError for
    ``@classmethod`` descriptors resolved via ``getattr(Cls, "get")``.
    Prefer setting on the underlying function; wrap if needed.
    """
    target = endpoint
    # Unwrap classmethod/staticmethod/bound method to raw function when possible
    if hasattr(endpoint, "__func__"):
        target = endpoint.__func__
    try:
        setattr(target, "name", name)
        return endpoint
    except (AttributeError, TypeError):
        pass

    # Last resort: wrap callable carrying .name for url_path_for / htmx helpers
    def _wrapped(*args, **kwargs):
        return endpoint(*args, **kwargs)

    _wrapped.name = name  # type: ignore[attr-defined]
    _wrapped.__name__ = getattr(endpoint, "__name__", name)
    _wrapped.__doc__ = getattr(endpoint, "__doc__", None)
    _wrapped.__wrapped__ = endpoint  # type: ignore[attr-defined]
    return _wrapped


def _clean_url_prefix(relative_file_folder: str, base_directory: str) -> str:
    """Derive URL prefix from a filesystem-relative folder under base_directory.

    Fixes:
    * ``str.replace(base, "")`` substring corruption (``application`` → ``lication``)
    * double-stripping ``app/app/...``
    * empty segments producing ``//``
    * private ``_`` segments removed from URL only
    * ``.`` / ``..`` never appear in the URL (path-traversal hardening)
    """
    # Normalize separators to /
    rel = relative_file_folder.replace("\\", "/").strip("/")
    base = base_directory.replace("\\", "/").strip("/")

    if rel == base:
        parts: List[str] = []
    elif rel.startswith(base + "/"):
        parts = rel[len(base) + 1 :].split("/")
    else:
        parts = rel.split("/") if rel else []

    # Drop private/empty; resolve . and .. so URLs cannot escape the base prefix
    cleaned: List[str] = []
    for part in parts:
        if not part or part.startswith("_") or part == ".":
            continue
        if part == "..":
            if not cleaned:
                # Would escape above base_directory — refuse entire prefix
                return ""
            cleaned.pop()
            continue
        cleaned.append(part)
    if not cleaned:
        return ""
    return "/" + "/".join(cleaned)


def _to_fastapi_path_params(prefix: str) -> str:
    """Convert Next-like ``[id]`` folder segments to FastAPI ``{id}``.

    Leaves existing ``{id}`` segments unchanged. Does not implement catch-all
    ``[...slug]`` yet.
    """
    if not prefix:
        return prefix
    segs = []
    for seg in prefix.split("/"):
        if not seg:
            continue
        if len(seg) >= 2 and seg[0] == "[" and seg[-1] == "]":
            inner = seg[1:-1]
            if inner.startswith("..."):
                # FastAPI path-convert not standard — keep raw for now
                segs.append(seg)
            else:
                segs.append("{" + inner + "}")
        else:
            segs.append(seg)
    return ("/" + "/".join(segs)) if segs else ""


class DirectoryRouter(routing.APIRouter):
    # picked from https://github.com/ebubekir/fastapi-directory-routing
    _METHODS = ["get", "post", "put", "patch", "delete", "head", "options"]

    """DirectoryRouter — Next.js-like file-based routes for ux-dom Components.

    Args:
        base_directory: Folder to scan (default ``app``).
        route_file_name: Stem for CRUD modules (default ``route`` → ``route.py``).
        package_dir: Explicit package root containing ``base_directory``.
            If omitted, uses ``Path(__main__.__file__).parent`` (fallback) with a
            warning — prefer passing ``package_dir`` for uvicorn/pytest.

    Path cleaning rules:
        * URL prefix is path-prefix relative to ``base_directory`` (not str.replace)
        * Segments starting with ``_`` are omitted from the URL (still imported)
        * ``[id]`` segments become ``{id}`` FastAPI path params
        * Class names keep original casing in URLs (no forced ``.lower()``)
    """

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
        # Drop keys APIRouter on this FastAPI version rejects
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
            "DirectoryRouter using __main__.__file__ root %s; "
            "pass package_dir= for reliable uvicorn/pytest discovery",
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

        files = sorted(base.rglob("*.py"))
        for file in files:
            if file.name == "__init__.py":
                continue  # import side-effect only packages when needed via modules
            # Private modules/packages: leading underscore (Next-style private)
            if file.stem.startswith("_") or any(
                part.startswith("_") for part in file.relative_to(parent).parts[:-1]
            ):
                logger.debug("DirectoryRouter skip private path %s", file)
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
                logger.exception(
                    "DirectoryRouter failed to import %s (%s)", module, file
                )
                continue

            if file.stem == self.route_file_name:
                # route.py: support BOTH Component classes (routes=) and bare HTTP verbs.
                # Bare verbs alone used to be the only path — Components in route.py were
                # silently ignored (brittle for `uxdom add route users/[id]`).
                class_map: dict = defaultdict(dict)
                if hasattr(route_file, "__all__"):
                    exported = list(route_file.__all__)
                else:
                    exported = [r for r in dir(route_file) if not r.startswith("_")]
                for klass_name in exported:
                    klass = getattr(route_file, klass_name, None)
                    if isinstance(klass, type) and getattr(klass, "routes", None):
                        for mthd in klass.routes:
                            if hasattr(klass, mthd):
                                class_map[klass_name][mthd] = getattr(klass, mthd)
                if class_map:
                    route_methods = class_map
                    kind = "component"
                else:
                    # Prefer explicit __all__; otherwise only HTTP verb callables
                    # (never every public name — that registered html tag imports as routes).
                    if hasattr(route_file, "__all__"):
                        route_methods = list(route_file.__all__)
                    else:
                        route_methods = [
                            r
                            for r in dir(route_file)
                            if r.lower() in self._METHODS
                            and callable(getattr(route_file, r, None))
                            and not isinstance(getattr(route_file, r, None), type)
                        ]
                    route_methods = [
                        r
                        for r in route_methods
                        if callable(getattr(route_file, r, None))
                    ]
                    kind = "route_module"
            else:
                route_methods = {}  # type: ignore
                if hasattr(route_file, "__all__"):
                    exported = list(route_file.__all__)
                else:
                    # Discover Component classes with ``routes=`` and bare HTTP
                    # callables. Do not require __all__ for production apps.
                    exported = []
                    for r in dir(route_file):
                        if r.startswith("_"):
                            continue
                        obj = getattr(route_file, r, None)
                        if obj is None:
                            continue
                        if isinstance(obj, type) and getattr(obj, "routes", None):
                            exported.append(r)
                        elif (
                            r.lower() in self._METHODS
                            and callable(obj)
                            and not isinstance(obj, type)
                        ):
                            exported.append(r)
                class_map: dict = defaultdict(dict)
                file_fns: dict = {}
                for klass_name in exported:
                    klass = getattr(route_file, klass_name, None)
                    if klass is None:
                        continue
                    routes_attr = getattr(klass, "routes", None)
                    if routes_attr:
                        for mthd in routes_attr:
                            if not hasattr(klass, mthd):
                                logger.error(
                                    "DirectoryRouter: %s.routes lists %r but method missing",
                                    klass_name,
                                    mthd,
                                )
                                continue
                            # preserve original class name casing in key
                            class_map[klass_name][mthd] = getattr(klass, mthd)
                    elif callable(klass) and not isinstance(klass, type):
                        file_fns[klass_name] = klass
                    elif isinstance(klass, type):
                        # class without routes= — skip (not auto REST)
                        pass
                if class_map:
                    route_methods = class_map
                    kind = "component"
                elif file_fns:
                    route_methods = file_fns
                    kind = "file_fns"
                else:
                    kind = "empty"

            if not route_methods:
                continue

            tags = (
                ["default"]
                if relative_file_folder == self.base_directory
                else relative_file_folder.split("/")
            )
            prefix = _clean_url_prefix(relative_file_folder, self.base_directory)
            prefix = _to_fastapi_path_params(prefix)

            _router = (
                routing.APIRouter(prefix=prefix, tags=tags)
                if prefix
                else routing.APIRouter(tags=tags)
            )
            _router.route_class = self.route_class

            if kind == "route_module":
                assert isinstance(route_methods, list)
                for method in route_methods:
                    _method_attr = getattr(route_file, method)
                    name = f"{module}:{method}"
                    _method_attr = _set_endpoint_name(_method_attr, name)
                    path = (
                        "/" if method.lower() in self._METHODS else f"/{method.lower()}"
                    )
                    methods = (
                        [method.lower()] if method.lower() in self._METHODS else ["get"]
                    )
                    self._add(_router, path, _method_attr, name, methods)
            elif kind == "component":
                assert isinstance(route_methods, dict)
                for klass_name, methods_map in route_methods.items():
                    for _method, _method_attr in methods_map.items():
                        name = f"{module}.{klass_name}.{_method}"
                        _method_attr = _set_endpoint_name(_method_attr, name)
                        mlow = _method.lower()
                        if mlow in self._METHODS:
                            # ``route.py`` is a segment placeholder (Next-style): URL is
                            # /{ClassName} under the folder prefix, not /route/ClassName.
                            if file.stem == self.route_file_name:
                                _route_ = (
                                    f"/{klass_name}"
                                    if not klass_name.startswith("_")
                                    else "/"
                                )
                            elif not file.stem.startswith("_"):
                                _route_ = (
                                    f"/{file.stem}/{klass_name}"
                                    if not klass_name.startswith("_")
                                    else f"/{file.stem}"
                                )
                            else:
                                _route_ = (
                                    f"/{klass_name}"
                                    if not klass_name.startswith("_")
                                    else "/"
                                )
                            methods = [mlow]
                        else:
                            if not file.stem.startswith("_"):
                                _route_ = (
                                    f"/{file.stem}/{klass_name}/{mlow}"
                                    if not klass_name.startswith("_")
                                    else f"/{file.stem}/{mlow}"
                                )
                            else:
                                _route_ = (
                                    f"/{klass_name}/{mlow}"
                                    if not klass_name.startswith("_")
                                    else f"/{mlow}"
                                )
                            methods = ["get"]
                        self._add(_router, _route_, _method_attr, name, methods)
            elif kind == "file_fns":
                assert isinstance(route_methods, dict)
                for fn_name, fn in route_methods.items():
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
        """Ensure static paths are matched before ``{param}`` segments.

        FastAPI/Starlette first-match wins. Without this, ``/products/{id}``
        can swallow ``/products/list/...`` siblings depending on include order.
        Nested routers are left intact; we only reorder *this* router's routes
        and one level of included APIRouter.routes when present.
        """

        def split(routes):
            static, dynamic = [], []
            for route in routes:
                path = getattr(route, "path", "") or ""
                # Mount/Host may lack path
                if "{" in path:
                    dynamic.append(route)
                else:
                    static.append(route)
            return static + dynamic

        self.routes[:] = split(list(self.routes))
        for route in list(self.routes):
            # Included sub-routers expose .app or .routes
            sub = getattr(route, "app", None) or getattr(route, "router", None)
            if (
                sub is not None
                and hasattr(sub, "routes")
                and isinstance(sub.routes, list)
            ):
                try:
                    sub.routes[:] = split(list(sub.routes))
                except Exception:
                    pass

    def _add(self, router, path, endpoint, name, methods):
        key = (router.prefix + path, tuple(sorted(methods)))
        if key in self._seen_routes:
            logger.warning(
                "DirectoryRouter duplicate route skipped: %s %s name=%s",
                methods,
                key[0],
                name,
            )
            return
        self._seen_routes.add(key)
        router.add_api_route(
            path,
            endpoint,
            name=name,
            methods=methods,
            description=getattr(endpoint, "__doc__", None),
        )

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
