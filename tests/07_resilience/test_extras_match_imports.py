"""ADR 0003 rule 2 — ux-dom extras carry only packages src/ux_dom imports."""
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _poetry() -> dict:
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    return data["tool"]["poetry"]


def test_only_fastapi_extra():
    # fastapi brings starlette for ux_dom.response.starlette.
    assert _poetry()["extras"] == {"fastapi": ["fastapi"]}


def test_product_packages_not_optional_runtime_deps():
    # Tailwind is ux-compose's (ux-compose #116 D3); uvicorn and
    # python-multipart are a host's choice, not imported by ux_dom.
    deps = {name.lower() for name in _poetry()["dependencies"]}
    assert not deps & {"pytailwindcss", "uvicorn", "python-multipart"}


def test_doctor_does_not_send_users_to_an_extra_for_uvicorn(tmp_path):
    from ux_dom.cli.doctor import run_doctor

    names = {c.name for c in run_doctor(cwd=tmp_path, port=59993).checks}
    assert "dep:fastapi" in names
    assert "dep:uvicorn" not in names
