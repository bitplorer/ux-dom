"""Dev tunnel providers for ``uxdom serve --tunnel``.

Providers (optional binaries on PATH):

* ``ngrok``      — ``ngrok http <target>``; URL from local API ``:4040``
* ``cloudflare`` — ``cloudflared tunnel --url http://<probe-host>:<port>``

Tunnel starts **after** local ``/health`` (or fallback) is green so the public
URL is never advertised against a dead origin (the classic tunnel 502).

Design / why / non-goals: ``docs/guides/TUNNEL.md``.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Literal, Optional

from ux_dom.utils.logger import ux_dom_logger

Provider = Literal["none", "ngrok", "cloudflare"]

__all__ = [
    "Provider",
    "TunnelHandle",
    "parse_provider",
    "local_probe_host",
    "wait_for_health",
    "start_tunnel",
    "provider_available",
]


@dataclass
class TunnelHandle:
    provider: str
    public_url: str
    process: subprocess.Popen

    def close(self, timeout: float = 5.0) -> None:
        if self.process.poll() is not None:
            return
        self.process.terminate()
        try:
            self.process.wait(timeout=timeout)
        except Exception:
            self.process.kill()


def parse_provider(value: Optional[str]) -> Provider:
    raw = (value or "none").strip().lower()
    aliases = {
        "none": "none",
        "off": "none",
        "false": "none",
        "0": "none",
        "ngrok": "ngrok",
        "cloudflare": "cloudflare",
        "cf": "cloudflare",
        "cloudflared": "cloudflare",
        "trycloudflare": "cloudflare",
    }
    if raw not in aliases:
        raise ValueError(
            f"unknown tunnel provider {value!r}; use none|ngrok|cloudflare"
        )
    return aliases[raw]  # type: ignore[return-value]


def local_probe_host(bind_host: str) -> str:
    """Host a *client* uses to reach the origin on this machine.

    Uvicorn may bind ``0.0.0.0`` / ``::`` (all interfaces). Those are not valid
    connection targets, so we probe loopback. A concrete bind (``127.0.0.1``,
    LAN IP, hostname) is used as-is.
    """
    h = (bind_host or "").strip().lower()
    if not h or h in {"0.0.0.0", "::", "[::]", "*"}:
        return "127.0.0.1"
    if h.startswith("[") and h.endswith("]"):
        return h[1:-1]
    return bind_host.strip()


def provider_available(provider: Provider) -> bool:
    if provider == "none":
        return True
    if provider == "ngrok":
        return shutil.which("ngrok") is not None
    if provider == "cloudflare":
        return shutil.which("cloudflared") is not None
    return False


def wait_for_health(
    port: int,
    *,
    host: str = "127.0.0.1",
    path: str = "/health",
    timeout: float = 30.0,
    interval: float = 0.25,
) -> str:
    """Block until origin answers on ``host:port``. Tries ``path`` then ``/``.

    ``host`` should be a *probe* address (see ``local_probe_host``), not a
    wildcard bind. Raises ``TimeoutError`` if the origin never becomes ready —
    the usual root cause of tunnel/edge **502**.
    """
    probe = local_probe_host(host)
    paths: list[str] = []
    for p in (path, "/"):
        if p and p not in paths:
            paths.append(p)
    deadline = time.monotonic() + max(timeout, 1.0)
    last_err: Optional[BaseException] = None
    while time.monotonic() < deadline:
        for p in paths:
            path_part = p if p.startswith("/") else "/" + p
            host_part = (
                f"[{probe}]" if ":" in probe and not probe.startswith("[") else probe
            )
            url = f"http://{host_part}:{port}{path_part}"
            try:
                with urllib.request.urlopen(url, timeout=1.5) as resp:
                    if 200 <= getattr(resp, "status", 200) < 500:
                        return p
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                last_err = exc
        time.sleep(interval)
    raise TimeoutError(
        f"origin http://{probe}:{port} not healthy within {timeout:.0f}s "
        f"(tried {', '.join(paths)}). Tunnel/edge 502 usually means this — "
        f"process down or still starting. last={last_err!r}"
    )


def _ngrok_url_from_api(timeout: float = 20.0) -> str:
    deadline = time.monotonic() + timeout
    last: Optional[BaseException] = None
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(
                "http://127.0.0.1:4040/api/tunnels", timeout=1.5
            ) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            for t in data.get("tunnels") or []:
                pub = t.get("public_url") or ""
                if pub.startswith("https://"):
                    return pub
            for t in data.get("tunnels") or []:
                pub = t.get("public_url") or ""
                if pub.startswith("http://"):
                    return pub
        except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
            last = exc
        time.sleep(0.25)
    raise TimeoutError(f"ngrok API :4040 had no public_url ({last!r})")


_CF_URL_RE = re.compile(
    r"https://[a-z0-9-]+\.trycloudflare\.com",
    re.IGNORECASE,
)


def _start_ngrok(
    port: int, token: Optional[str], *, target_host: str = "127.0.0.1"
) -> TunnelHandle:
    bin_path = shutil.which("ngrok")
    if not bin_path:
        raise FileNotFoundError(
            "ngrok not on PATH. Install: https://ngrok.com/download "
            "or `brew install ngrok` / package manager."
        )
    env = os.environ.copy()
    if token:
        env["NGROK_AUTHTOKEN"] = token
    elif not env.get("NGROK_AUTHTOKEN"):
        ux_dom_logger.info(
            "tunnel[ngrok]: NGROK_AUTHTOKEN not set — free accounts may need "
            "`ngrok config add-authtoken …`"
        )
    probe = local_probe_host(target_host)
    target = str(port) if probe in {"127.0.0.1", "localhost"} else f"{probe}:{port}"
    proc = subprocess.Popen(
        [bin_path, "http", target, "--log=stdout", "--log-format=logfmt"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env=env,
    )
    try:
        url = _ngrok_url_from_api()
    except Exception:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except Exception:
            proc.kill()
        raise
    return TunnelHandle(provider="ngrok", public_url=url, process=proc)


def _start_cloudflare(
    port: int, token: Optional[str], *, target_host: str = "127.0.0.1"
) -> TunnelHandle:
    bin_path = shutil.which("cloudflared")
    if not bin_path:
        raise FileNotFoundError(
            "cloudflared not on PATH. Install: "
            "https://developers.cloudflare.com/cloudflare-one/connections/"
            "connect-apps/install-and-setup/installation/"
        )
    env = os.environ.copy()
    if token:
        env.setdefault("TUNNEL_TOKEN", token)
    probe = local_probe_host(target_host)
    proc = subprocess.Popen(
        [
            bin_path,
            "tunnel",
            "--url",
            f"http://{probe}:{port}",
            "--no-autoupdate",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env=env,
        text=True,
        bufsize=1,
    )
    deadline = time.monotonic() + 30.0
    lines: list[str] = []
    assert proc.stdout is not None
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            rest = proc.stdout.read() or ""
            raise RuntimeError(
                f"cloudflared exited {proc.returncode}: {rest or ''.join(lines[-20:])}"
            )
        line = proc.stdout.readline()
        if not line:
            time.sleep(0.05)
            continue
        lines.append(line)
        m = _CF_URL_RE.search(line)
        if m:
            return TunnelHandle(
                provider="cloudflare", public_url=m.group(0), process=proc
            )
    proc.terminate()
    try:
        proc.wait(timeout=3)
    except Exception:
        proc.kill()
    raise TimeoutError(
        "cloudflared did not print a trycloudflare.com URL in time. "
        f"tail={''.join(lines[-10:])!r}"
    )


def start_tunnel(
    provider: Provider,
    port: int,
    *,
    token: Optional[str] = None,
    host: str = "127.0.0.1",
) -> Optional[TunnelHandle]:
    """Start a public tunnel to the local origin. ``none`` → ``None``.

    ``host`` is the uvicorn bind host; wildcards map to loopback via
    ``local_probe_host`` so the tunnel targets a reachable address.
    """
    if provider == "none":
        return None
    if provider == "ngrok":
        return _start_ngrok(port, token, target_host=host)
    if provider == "cloudflare":
        return _start_cloudflare(port, token, target_host=host)
    raise ValueError(f"unknown tunnel provider {provider!r}")
