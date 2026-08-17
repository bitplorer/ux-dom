"""Public tunnel helpers for uxdom serve / dev / start.

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
    """Running tunnel process + public URL (when known)."""

    provider: Provider
    process: subprocess.Popen
    public_url: Optional[str] = None

    def stop(self) -> None:
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()


def parse_provider(value: Optional[str]) -> Provider:
    if not value:
        return "none"
    raw = value.strip().lower()
    aliases = {
        "none": "none",
        "off": "none",
        "false": "none",
        "0": "none",
        "ngrok": "ngrok",
        "cloudflare": "cloudflare",
        "cf": "cloudflare",
        "cloudflared": "cloudflare",
    }
    if raw not in aliases:
        raise ValueError(
            f"unknown tunnel provider {value!r}; expected none|ngrok|cloudflare"
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
    deadline = time.monotonic() + timeout
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
            except BaseException as exc:
                last_err = exc
        time.sleep(interval)
    raise TimeoutError(
        f"origin http://{probe}:{port} not healthy within {timeout:.0f}s "
        f"(tried {', '.join(paths)}). Tunnel/edge 502 usually means this — "
        f"process down or still starting. last={last_err!r}"
    )


def _ngrok_public_url(timeout: float = 15.0) -> Optional[str]:
    """Poll ngrok local API for the public HTTPS URL."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen("http://127.0.0.1:4040/api/tunnels", timeout=1.5) as resp:
                data = json.loads(resp.read().decode())
            for t in data.get("tunnels") or []:
                url = t.get("public_url") or ""
                if url.startswith("https://"):
                    return url
                if url.startswith("http://") and not url.startswith("http://127"):
                    return url
        except BaseException:
            pass
        time.sleep(0.3)
    return None


_CF_URL_RE = re.compile(
    r"https://[a-z0-9-]+\.trycloudflare\.com",
    re.IGNORECASE,
)


def _cloudflare_public_url(proc: subprocess.Popen, timeout: float = 20.0) -> Optional[str]:
    """Parse cloudflared stderr for the trycloudflare.com URL."""
    deadline = time.monotonic() + timeout
    buf = ""
    while time.monotonic() < deadline:
        if proc.stderr is None:
            break
        line = proc.stderr.readline()
        if not line:
            if proc.poll() is not None:
                break
            time.sleep(0.1)
            continue
        if isinstance(line, bytes):
            line = line.decode(errors="replace")
        buf += line
        m = _CF_URL_RE.search(buf)
        if m:
            return m.group(0)
    m = _CF_URL_RE.search(buf)
    return m.group(0) if m else None


def start_tunnel(
    provider: Provider,
    port: int,
    *,
    host: str = "127.0.0.1",
    token: Optional[str] = None,
) -> TunnelHandle:
    """Start tunnel process targeting probe host:port. Caller must have waited for health."""
    if provider == "none":
        raise ValueError("start_tunnel called with provider=none")
    probe = local_probe_host(host)
    target = f"{probe}:{port}"

    if provider == "ngrok":
        if not shutil.which("ngrok"):
            raise FileNotFoundError(
                "ngrok binary not found on PATH. Install from https://ngrok.com/download "
                "or set --tunnel none."
            )
        env = os.environ.copy()
        if token:
            env["NGROK_AUTHTOKEN"] = token
        # ngrok http <addr>
        cmd = ["ngrok", "http", target, "--log=stdout"]
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env=env,
            text=True,
        )
        public = _ngrok_public_url()
        return TunnelHandle(provider="ngrok", process=proc, public_url=public)

    if provider == "cloudflare":
        if not shutil.which("cloudflared"):
            raise FileNotFoundError(
                "cloudflared binary not found on PATH. Install from "
                "https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/installation/ "
                "or set --tunnel none."
            )
        # Prefer probing the same host the origin bound to when concrete.
        url = f"http://{probe}:{port}"
        cmd = ["cloudflared", "tunnel", "--url", url]
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        public = _cloudflare_public_url(proc)
        return TunnelHandle(provider="cloudflare", process=proc, public_url=public)

    raise ValueError(f"unsupported provider {provider!r}")
