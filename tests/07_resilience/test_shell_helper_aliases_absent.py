"""ADR 0004 absence lock: one name per shell helper.

``Document.runtime_tags``, ``App.use``, ``App.shell_fragments``,
``plugins.shell.shell_fragments`` and ``Csp`` are the only names. ``App.build()``
without ``asgi=`` raises ``TypeError`` (the ``ProductHostMoved`` tombstone is gone).
"""

from __future__ import annotations

import pytest

import ux_dom.plugins as plugins
import ux_dom.plugins.csp as csp
import ux_dom.plugins.hub as hub
import ux_dom.plugins.shell as shell
from ux_dom.plugins.hub import App
from ux_dom.settings.document import Document


@pytest.mark.parametrize("name", ["runtime_tags", "CspNonce", "shell_fragments_nonced"])
def test_plugins_do_not_export(name: str):
    assert name not in plugins.__all__
    assert not hasattr(plugins, name)


@pytest.mark.parametrize("name", ["runtime_tags", "plugins", "fastapi"])
def test_app_has_no_alias(name: str):
    assert not hasattr(App, name)


@pytest.mark.parametrize(
    ("module", "name"),
    [
        (shell, "runtime_tags"),
        (csp, "CspNonce"),
        (csp, "shell_fragments_nonced"),
        (hub, "ProductHostMoved"),
    ],
)
def test_module_has_no_alias(module, name: str):
    assert not hasattr(module, name)


def test_document_has_no_plugin_head_body():
    assert not hasattr(Document, "plugin_head_body")
    assert hasattr(Document, "runtime_tags")


def test_build_without_asgi_is_type_error():
    with pytest.raises(TypeError, match="asgi="):
        App().build()
