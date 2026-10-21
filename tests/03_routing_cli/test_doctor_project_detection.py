"""uxdom doctor detects a pure-dom project by ``app/main.py`` alone (#106).

``app/settings.py`` is product-layout residue (ADR 0003) and no longer gates the
project rows. Doctor reads the project; it never imports or runs it.
"""

from __future__ import annotations

from pathlib import Path

from ux_dom.cli.doctor import run_doctor


def _main_tree(root: Path) -> Path:
    (root / "app").mkdir(parents=True)
    (root / "app" / "main.py").write_text("app = object()\n", encoding="utf-8")
    return root


def test_app_main_without_settings_is_a_project(tmp_path: Path):
    root = _main_tree(tmp_path / "p")
    rep = run_doctor(cwd=root)
    assert rep.project_root == root.resolve()
    assert "app/document.py" in {c.name for c in rep.checks}


def test_detection_walks_up_from_a_subfolder(tmp_path: Path):
    root = _main_tree(tmp_path / "p")
    assert run_doctor(cwd=root / "app").project_root == root.resolve()


def test_settings_alone_is_not_a_project(tmp_path: Path):
    (tmp_path / "app").mkdir()
    (tmp_path / "app" / "settings.py").write_text("DEBUG = True\n", encoding="utf-8")
    assert run_doctor(cwd=tmp_path).project_root is None


def test_product_app_py_is_not_a_pure_dom_project(tmp_path: Path):
    (tmp_path / "app.py").write_text("asgi = object()\n", encoding="utf-8")
    assert run_doctor(cwd=tmp_path).project_root is None


def test_no_always_green_app_main_row(tmp_path: Path):
    root = _main_tree(tmp_path / "p")
    (root / "app" / "settings.py").write_text("", encoding="utf-8")
    rep = run_doctor(cwd=root)
    assert rep.project_root == root.resolve()
    assert "app/main.py" not in {c.name for c in rep.checks}


def test_doctor_does_not_import_the_app(tmp_path: Path):
    root = _main_tree(tmp_path / "p")
    marker = tmp_path / "imported"
    (root / "app" / "main.py").write_text(
        f"open({str(marker)!r}, 'w').close()\nraise SystemExit(3)\n", encoding="utf-8"
    )
    rep = run_doctor(cwd=root)
    assert rep.project_root == root.resolve()
    assert not marker.exists()
