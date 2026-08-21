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
* accept_symbol(name, obj, module) → bool
* on_route(record) → None
"""
__all__ = ["HTMLRoute", "StreamingRoute", "DirectoryRouter", "RouterHooks", "DirectoryRouterError"]


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

_HTTP_VERBS = ("get", "post", "put", "patch", "delete", "head", "options")


class DirectoryRouterError(RuntimeError):
    """Fail-closed routing errors (ambiguous page, invalid export, etc.)."""


class RouterHooks:
    """Generic extension sockets for DirectoryRouter.

    All callables optional. Any host may pass hooks; ux-dom never imports
    host-specific types. With hooks=None, page GET uses ``cls()``.
    """

    __slots__ = ("resolve_unit", "accept_symbol", "on_route")

    def __init__(
        self,
        resolve_unit: Optional[Callable[..., Any]] = None,
        accept_symbol: Optional[Callable[..., bool]] = None,
        on_route: Optional[Callable[..., None]] = None,
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
            if isinstance(attr, staticmethod):
                attr = attr.__func__
            if isinstance(attr, classmethod):
                attr = attr.__func__
            if callable(attr):
                found[verb] = getattr(klass, verb)
    return found


def _page_get_endpoint(
    klass: type,
    *,
    path: str,
    name: str,
    resolve_unit: Optional[Callable[..., Any]] = None,
):
    """GET page serve via resolve_unit or Klass() — not a synthetic class method."""

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
    parts = safe.split(".")
    safe_name = "_".join(parts)
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


def _is_renderable_unit(klass: type) -> bool:
    return any(
        callable(getattr(klass, n, None))
        for n in ("render", "__render__", "__async_render__")
    )


def _default_get_endpoint(klass: type):
    """Backward-compatible page GET → fresh instance (prefer _page_get_endpoint)."""
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
    _METHODS = ["get", "post", "put", "patch", "delete", "head", "options"]

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
        default: Optional[ASGIApp]] = None,
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
