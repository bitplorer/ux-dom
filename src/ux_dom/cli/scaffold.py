# Copyright (c) 2026 ux-dom
"""Removed from the product path.

Sole product scaffold: ``uxcompose create-app``.
This module exists so leftover imports fail closed with a teaching error
instead of ``ModuleNotFoundError``.
"""

_MSG = (
    "ux_dom.cli.scaffold is not the product path. "
    "Use: uxcompose create-app <dest>  "
    "(see ux-compose docs/FLOW.md)."
)


def available_templates():
    raise ImportError(_MSG)


def create_app(*args, **kwargs):
    raise ImportError(_MSG)


def validate_scaffold(*args, **kwargs):
    raise ImportError(_MSG)


class ScaffoldOptions:
    def __init__(self, *args, **kwargs):
        raise ImportError(_MSG)
