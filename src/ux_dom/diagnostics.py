# Copyright (c) 2026 ux-dom
"""Human-friendly diagnostic helpers for common ux-dom mistakes."""

from __future__ import annotations


def xelement_missing_tagname(cls_name: str, element_qual: str) -> str:
    return (
        f"{cls_name}.{element_qual}: missing required attribute 'x-tagname'.\n"
        f"  Fix: return template(..., **{{'x-tagname': tag_name}})\n"
        f"  Host will be <x-{{tag_name}}> after x_element.js upgrades.\n"
        f"  See docs/XELEMENT.md"
    )


def xelement_light_with_shadow(cls_name: str, element_qual: str) -> str:
    return (
        f"{cls_name}.{element_qual}: CustomElement (light DOM) must not set "
        f"'shadowroot' or 'shadowdom'.\n"
        f"  Fix: use WebComponent for shadow DOM, or remove the shadow attribute.\n"
        f"  See docs/XELEMENT.md · examples/xelement_kit /lightdom vs /shadowdom"
    )


def xelement_shadow_missing(cls_name: str, element_qual: str) -> str:
    return (
        f"{cls_name}.{element_qual}: WebComponent (shadow DOM) requires "
        f"'shadowroot' or 'shadowdom' on the definition template.\n"
        f"  Fix: template(..., **{{'x-tagname': tag_name, 'shadowroot': 'true'}})\n"
        f"  See docs/XELEMENT.md"
    )


def directory_router_missing_base(base: str) -> str:
    return (
        f"DirectoryRouter base_directory does not exist: {base}\n"
        f"  Fix: create the folder or pass package_dir= to the app package root.\n"
        f"  create-app layout: package_dir=Path(__file__).parent, base_directory='routes'"
    )


def directory_router_no_package_dir() -> str:
    return (
        "DirectoryRouter cannot resolve package root.\n"
        "  Fix: DirectoryRouter(package_dir=Path(__file__).resolve().parent, "
        "base_directory='routes')\n"
        "  Prefer package_dir= over __main__.__file__ discovery."
    )
