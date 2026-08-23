"""Removed from product path.

Sole product scaffold: ``uxcompose create-app``.
"""

raise ImportError(
    "ux_dom.cli.scaffold is not the product path. Use: uxcompose create-app <dest>"
)


def available_templates():
    raise ImportError("uxcompose create-app is the product scaffold")


def create_app(*args, **kwargs):
    raise ImportError("uxcompose create-app is the product scaffold")


class ScaffoldOptions:
    def __init__(self, *args, **kwargs):
        raise ImportError("uxcompose create-app is the product scaffold")
