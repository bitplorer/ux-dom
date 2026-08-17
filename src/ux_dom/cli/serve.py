"""Next-style process runner — ``uxdom serve`` / ``dev`` / ``start``.

``dev``     → reload + Tailwind watch  (next dev)
``serve``   → same as dev unless ``--prod``
``start``   → production, no reload, minify CSS (next start)

Tailwind is the official standalone CLI (PATH / pytailwindcss / cache download).
HMR stays on the Document/app lifespan — this process only starts uvicorn + CSS.

When this runner owns Tailwind it sets ``UXDOM_TAILWIND_OWNED=1`` so the
in-app ``TailwindStyle`` lifespan does not spawn a second watcher.

Tunneling (``--tunnel ngrok|cloudflare``)
----------------------------------------
Origin is started first; we **wait for local health** before opening a public
tunnel and printing the URL. That avoids the classic edge **502** where the
tunnel is up but uvicorn is not.
"""
from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from ux_dom.utils.logger import ux_dom_logger

__all__ = ["ServeOptions", "find_app_root", "run_serve"]

# Lifespan plugins honor this so CLI and Document do not double-run Tailwind.
TAILWIND_OWNED_ENV = "UXDOM_TAILWIND_OWNED"


def find_app_root(start: Optional[Path] = None) -> Path:
    cur = (start or Path.cwd()).resolve()
    for p in [cur, *cur.parents]:
        if (p / "app" / "main.py").is_file():
            return p
        if p == p.parent:
            break
    raise FileNotFoundError(
        "no ux-dom app found (expected app/main.py). "
        "Run from a create-app project, or pass --cwd / an import path."
    )


@dataclass
class ServeOptions:
    app_import: str = "app.main:app"
    host: str = "0.0.0.0"
    port: int = 8080
    mode: str = "dev"  # dev | prod
    reload: Optional[bool] = None
    tailwind: bool = True
    cwd: Optional[Path] = None
    # Tunnel DX — none | ngrok | cloudflare
    tunnel: str = "none"
    tunnel_token: Optional[str] = None
    health_path: str = "/health"
    health_timeout: float = 30.0

    def __post_init__(self) -> None:
        if self.mode not in {"dev", "prod"}:
            raise ValueError(f"mode must be dev|prod, got {self.mode!r}")
        if self.reload is None:
            self.reload = self.mode == "dev"
        if self.cwd is not None:
            self.cwd = Path(self.cwd).resolve()
        from ux_dom.cli.tunnel import parse_provider

        self.tunnel = parse_provider(self.tunnel)


def _prepare_path(root: Path) -> None:
    cwd = str(root)
    os.environ["PYTHONPATH"] = (
        cwd + os.pathsep + os.environ["PYTHONPATH"]
        if os.environ.get("PYTHONPATH")
        else cwd
    )
    if cwd not in sys.path:
        sys.path.insert(0, cwd)


def _run_tailwind(root: Path, *, minify: bool, watch: bool) -> Optional[subprocess.Popen]:
    from ux_dom.cli.tailwind import argv_with_io, discover_css_io, resolve_tailwind

    io = discover_css_io(root)
    if io is None:
        ux_dom_logger.info("tailwind: no assets/css/input.css — skip")
        return None
    hit = resolve_tailwind(cwd=root, ensure=True)
    if not hit:
        ux_dom_logger.warning(
            "tailwind: standalone CLI not found "
            "(pip install pytailwindcss · or npm i -D @tailwindcss/cli)"
        )
        return None
    input_css, output_css = io
    cmd = argv_with_io(
        hit.argv, input_css=input_css, output_css=output_css, minify=minify, watch=watch
    )
    ux_dom_logger.info(f"tailwind[{hit.source}]: " + " ".join(cmd))
    if watch:
        return subprocess.Popen(cmd, cwd=str(root))
    proc = subprocess.run(cmd, cwd=str(root))
    if proc.returncode != 0:
        ux_dom_logger.warning(f"tailwind exited {proc.returncode}")
    return None


def _banner(opts: ServeOptions, root: Path, tw: str, public_url: Optional[str] = None) -> None:
    mode = "prod" if opts.mode == "prod" else "dev"
    from ux_dom.cli.tunnel import local_probe_host

    local = f"http://{local_probe_host(opts.host)}:{opts.port}"
    ux_dom_logger.info(f"uxdom {mode}  ·  {opts.app_import}")
    ux_dom_logger.info(f"  local     {local}")
    ux_dom_logger.info(f"  network   http://{opts.host}:{opts.port}")
    if public_url:
        ux_dom_logger.info(f"  public    {public_url}")
    ux_dom_logger.info(f"  root      {root}")
    ux_dom_logger.info(f"  tailwind  {tw}")
    ux_dom_logger.info(f"  reload    {bool(opts.reload)}")
    ux_dom_logger.info(f"  tunnel    {opts.tunnel}")
    ux_dom_logger.info("  hmr       app lifespan (create-app WITH_HMR)")


def _uvicorn_argv(opts: ServeOptions) -> list[str]:
    cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        opts.app_import,
        "--host",
        opts.host,
        "--port",
        str(opts.port),
    ]
    if opts.reload:
        cmd.append("--reload")
    return cmd


def _serve_with_tunnel(
    opts: ServeOptions,
    root: Path,
    tw_note: str,
    watcher: Optional[subprocess.Popen],
) -> None:
    """Subprocess uvicorn → health gate → tunnel → wait; cleanup on exit."""
    from ux_dom.cli.tunnel import start_tunnel, wait_for_health

    server: Optional[subprocess.Popen] = None
    tunnel = None
    try:
        cmd = _uvicorn_argv(opts)
        ux_dom_logger.info("uvicorn: " + " ".join(cmd))
        server = subprocess.Popen(cmd, cwd=str(root))
        try:
            healthy_path = wait_for_health(
                opts.port,
                host=opts.host,
                path=opts.health_path,
                timeout=opts.health_timeout,
            )
            ux_dom_logger.info(f"health    ok  ({healthy_path})")
        except TimeoutError as exc:
            ux_dom_logger.error(str(exc))
            raise SystemExit(1) from exc

        try:
            tunnel = start_tunnel(
                opts.tunnel,  # type: ignore[arg-type]
                opts.port,
                token=opts.tunnel_token
                or os.environ.get("NGROK_AUTHTOKEN")
                or os.environ.get("TUNNEL_TOKEN"),
                host=opts.host,
            )
        except FileNotFoundError as exc:
            ux_dom_logger.error(str(exc))
            raise SystemExit(1) from exc
        except Exception as exc:
            ux_dom_logger.error(f"tunnel failed: {exc}")
            raise SystemExit(1) from exc

        public = tunnel.public_url if tunnel else None
        _banner(opts, root, tw_note, public_url=public)
        if public:
            ux_dom_logger.info(f"tunnel[{opts.tunnel}] ready — open {public}")

        assert server is not None
        while True:
            code = server.poll()
            if code is not None:
                ux_dom_logger.error(f"uvicorn exited {code}")
                raise SystemExit(code or 1)
            if tunnel is not None and tunnel.process.poll() is not None:
                ux_dom_logger.error(
                    f"tunnel[{opts.tunnel}] exited {tunnel.process.returncode}"
                )
                raise SystemExit(1)
            time.sleep(0.4)
    except KeyboardInterrupt:
        ux_dom_logger.info("shutting down")
    finally:
        if tunnel is not None:
            tunnel.close()
        if server is not None and server.poll() is None:
            server.send_signal(signal.SIGTERM)
            try:
                server.wait(timeout=8)
            except Exception:
                server.kill()
        if watcher is not None and watcher.poll() is None:
            watcher.terminate()
            try:
                watcher.wait(timeout=5)
            except Exception:
                watcher.kill()


def run_serve(opts: ServeOptions) -> None:
    """Start Tailwind (optional) then uvicorn. Blocks.

    With ``tunnel != none``: subprocess origin, health gate, then tunnel so the
    public URL is never printed against a dead host.
    """
    try:
        import uvicorn  # noqa: F401
    except ImportError as e:
        ux_dom_logger.error(
            "uvicorn is required for `uxdom serve` / `uxdom dev`. "
            "Install with: pip install 'ux-dom[fastapi]'"
        )
        raise SystemExit(1) from e

    try:
        root = opts.cwd or find_app_root()
    except FileNotFoundError:
        root = (opts.cwd or Path.cwd()).resolve()

    from ux_dom.cli.envfile import load_env_files

    loaded = load_env_files(root, mode=opts.mode)
    if loaded:
        ux_dom_logger.info(
            "env: " + ", ".join(p.name for p in loaded) + " (process env wins)"
        )

    _prepare_path(root)
    if opts.mode == "prod":
        os.environ.setdefault("DEBUG", "0")

    tw_note = "off"
    watcher: Optional[subprocess.Popen] = None
    if opts.tailwind:
        os.environ[TAILWIND_OWNED_ENV] = "1"
        if opts.mode == "prod":
            _run_tailwind(root, minify=True, watch=False)
            tw_note = "minify"
        else:
            watcher = _run_tailwind(root, minify=False, watch=True)
            tw_note = "watch" if watcher is not None else "unavailable"

    if opts.tunnel != "none":
        _serve_with_tunnel(opts, root, tw_note, watcher)
        return

    _banner(opts, root, tw_note)
    try:
        import uvicorn

        uvicorn.run(
            opts.app_import,
            host=opts.host,
            port=opts.port,
            reload=bool(opts.reload),
        )
    finally:
        if watcher is not None and watcher.poll() is None:
            watcher.terminate()
            try:
                watcher.wait(timeout=5)
            except Exception:
                watcher.kill()
