# Copyright (c) 2026 ux-dom
"""Human-friendly diagnostic helpers for common ux-dom mistakes."""

from __future__ import annotations


def xelement_missing_tagname(cls_name: str, element_qual: str) -> str:
    return (
        f"{cls_name}.{element_qual}: missing required attribute 'x-tagname'.\n"
        f"  Fix: return template(..., **{{'x-tagname': tag_name}})\n"
        f"  Host will be <x-{{tag_name}}> after x_element.js upgrades.\n"
        f"  See docs/guides/XELEMENT.md"
    )


def xelement_light_with_shadow(cls_name: str, element_qual: str) -> str:
    return (
        f"{cls_name}.{element_qual}: CustomElement (light DOM) must not set "
        f"'shadowroot' or 'shadowdom'.\n"
        f"  Fix: use WebComponent for shadow DOM, or remove the shadow attribute.\n"
        f"  See docs/guides/XELEMENT.md · examples/xelement_kit /lightdom vs /shadowdom"
    )


def xelement_shadow_missing(cls_name: str, element_qual: str) -> str:
    return (
        f"{cls_name}.{element_qual}: WebComponent (shadow DOM) requires "
        f"'shadowroot' or 'shadowdom' on the definition template.\n"
        f"  Fix: template(..., **{{'x-tagname': tag_name, 'shadowroot': 'true'}})\n"
        f"  See docs/guides/XELEMENT.md"
    )
