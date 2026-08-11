# Copyright (c) 2026 ux-dom
"""``uxdom deploy`` — generate deploy configs + print provider instructions.

ux-dom apps are ASGI (typically FastAPI + uvicorn). This command does **not**
push to a cloud account (no secrets/API keys). It prepares artifacts and
checklists for common hosts.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, Optional

Provider = Literal["docker", "fly", "render", "railway", "vps", "checklist"]


@dataclass
class DeployResult:
    root: Path
    provider: str
    files_written: list[str] = field(default_factory=list)
    instructions: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "root": str(self.root),
            "provider": self.provider,
            "files_written": self.files_written,
            "instructions": self.instructions,
            "notes": self.notes,
        }


def _find_app_root(start: Optional[Path] = None) -> Path:
    cur = (start or Path.cwd()).resolve()
    for p in [cur, *cur.parents]:
        if (p / "app" / "main.py").is_file():
            return p
        if p == p.parent:
            break
    raise FileNotFoundError(
        "no ux-dom app found (expected app/main.py). Run from create-app root."
    )


def _write(path: Path, content: str, *, force: bool) -> bool:
    if path.exists() and not force:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    if not content.endswith("\n"):
        content += "\n"
    path.write_text(content, encoding="utf-8")
    return True


_DOCKERFILE = """\
# ux-dom ASGI production image
FROM python:3.14-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \\
    PYTHONUNBUFFERED=1 \\
    PORT=8080

RUN apt-get update && apt-get install -y --no-install-recommends \\
    curl \\
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -U pip \\
    && pip install --no-cache-dir -r requirements.txt \\
    && pip install --no-cache-dir "uvicorn[standard]" fastapi

COPY . .

# Optional production CSS (ignore failure if no tailwind in image)
RUN if [ -f app/tailwindcss.py ]; then python -m app.tailwindcss || true; fi

EXPOSE 8080
# Host platforms inject PORT — default 8080 for local docker run
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
"""

_DOCKERIGNORE = """\
.venv
__pycache__
*.pyc
.git
.env
.pytest_cache
*.egg-info
"""

_FLY = """\
# fly.toml — https://fly.io/docs/
app = "{app_name}"
primary_region = "iad"

[build]

[http_service]
  internal_port = 8080
  force_https = true
  auto_stop_machines = "stop"
  auto_start_machines = true
  min_machines_running = 0

[[vm]]
  memory = "512mb"
  cpu_kind = "shared"
  cpus = 1
"""

_RENDER = """\
# render.yaml — Blueprint
services:
  - type: web
    name: {app_name}
    runtime: python
    plan: free
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn app.main:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: PYTHON_VERSION
        value: "3.14.0"
      - key: DEBUG
        value: "false"
"""

_RAILWAY = """\
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "uvicorn app.main:app --host 0.0.0.0 --port $PORT",
    "restartPolicyType": "ON_FAILURE"
  }
}
"""

_SYSTEMD = """\
[Unit]
Description=ux-dom {app_name}
After=network.target

[Service]
User=www-data
WorkingDirectory=/var/www/{app_name}
Environment=DEBUG=false
Environment=PORT=8080
ExecStart=/var/www/{app_name}/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8080
Restart=always

[Install]
WantedBy=multi-user.target
"""


def prepare_deploy(
    provider: Provider = "docker",
    *,
    cwd: Optional[Path] = None,
    force: bool = False,
    app_name: Optional[str] = None,
) -> DeployResult:
    root = _find_app_root(cwd)
    name = app_name or root.name.replace("_", "-").lower()
    result = DeployResult(root=root, provider=provider)

    result.notes.append(
        "uxdom deploy does not upload to the cloud — it generates config + checklist."
    )
    result.notes.append(
        "Run `uxdom build` first. Set DEBUG=false and real secrets in the host env."
    )
    result.notes.append(
        "ASGI entrypoint: uvicorn app.main:app --host 0.0.0.0 --port $PORT"
    )

    if provider == "checklist":
        result.instructions = [
            "1. uxdom build",
            "2. uxdom doctor --prod",
            "3. Set SECRET_KEY / DEBUG=false / any UX_CHANNEL_* env",
            "4. Serve with: uvicorn app.main:app --host 0.0.0.0 --port 8080",
            "5. Put TLS reverse proxy (Caddy/nginx) in front",
            "6. Ensure assets/js/x_element.js is deployed with the app",
        ]
        return result

    if provider == "docker":
        if _write(root / "Dockerfile", _DOCKERFILE, force=force):
            result.files_written.append("Dockerfile")
        else:
            result.notes.append("Dockerfile exists (use --force to overwrite)")
        if _write(root / ".dockerignore", _DOCKERIGNORE, force=force):
            result.files_written.append(".dockerignore")
        result.instructions = [
            "docker build -t {name} .".format(name=name),
            "docker run --rm -p 8080:8080 -e DEBUG=false {name}".format(name=name),
            "# push to any registry, then run on Fly/Render/ECS/K8s/VPS",
        ]
    elif provider == "fly":
        # ensure Dockerfile for fly
        if not (root / "Dockerfile").exists():
            _write(root / "Dockerfile", _DOCKERFILE, force=True)
            result.files_written.append("Dockerfile")
        if _write(root / "fly.toml", _FLY.format(app_name=name), force=force):
            result.files_written.append("fly.toml")
        result.instructions = [
            "fly auth login",
            f"fly apps create {name}   # if needed",
            "fly deploy",
            "fly secrets set DEBUG=false SECRET_KEY=...",
        ]
    elif provider == "render":
        if _write(root / "render.yaml", _RENDER.format(app_name=name), force=force):
            result.files_written.append("render.yaml")
        result.instructions = [
            "Push repo to GitHub/GitLab",
            "Render Dashboard → New → Blueprint → select render.yaml",
            "Or Web Service: build pip install -r requirements.txt; start uvicorn …",
        ]
    elif provider == "railway":
        if _write(root / "railway.json", _RAILWAY, force=force):
            result.files_written.append("railway.json")
        result.instructions = [
            "railway login",
            "railway init && railway up",
            "Set DEBUG=false in Railway variables",
        ]
    elif provider == "vps":
        unit = f"deploy/{name}.service"
        if _write(root / unit, _SYSTEMD.format(app_name=name), force=force):
            result.files_written.append(unit)
        if not (root / "Dockerfile").exists():
            if _write(root / "Dockerfile", _DOCKERFILE, force=force):
                result.files_written.append("Dockerfile")
        result.instructions = [
            "rsync/git pull to /var/www/{name}".format(name=name),
            "python -m venv .venv && pip install -r requirements.txt",
            "uxdom build",
            f"sudo cp {unit} /etc/systemd/system/",
            "sudo systemctl enable --now " + name,
            "Configure Caddy/nginx TLS → 127.0.0.1:8080",
        ]
    else:
        raise ValueError(f"unknown provider {provider!r}")

    return result


def format_deploy_result(result: DeployResult) -> str:
    lines = [
        "ux-dom deploy prepare",
        f"provider: {result.provider}",
        f"root: {result.root}",
        "=" * 40,
    ]
    if result.files_written:
        lines.append("wrote:")
        for f in result.files_written:
            lines.append(f"  + {f}")
    else:
        lines.append("wrote: (no new files)")
    if result.notes:
        lines.append("notes:")
        for n in result.notes:
            lines.append(f"  · {n}")
    lines.append("next:")
    for i in result.instructions:
        lines.append(f"  $ {i}" if not i.startswith("#") else f"  {i}")
    lines.append("=" * 40)
    lines.append("Deploy configs ready — run host CLI / CI to publish.")
    return "\n".join(lines)
