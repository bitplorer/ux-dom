# Copyright (c) 2026 ux_dom
#
# This software is released under the MIT License.
# https://opensource.org/licenses/MIT
"""Document contributions and optional advanced hub.

**Document is the single source of truth** for the HTML shell::

    document = Document(...).use(XElement(), Htmx(), Csp.auto())
    document.mount(app)  # attaches contribution middleware to *caller*'s app

``Document.use`` owns shell meaning: control dialect, runtime script tags,
CSP stamp/policy, style tags.

**Not product composition:** ``App`` / ``PluginHub`` remain for tests and
advanced hubs only. Product applications use **ux-compose** ``App`` and
``uxcompose create-app``. Do not treat ``plugins.App.web`` as the product path.

HMR process (file watch + WebSocket) is **dev delivery** — product path is
ux-compose; ``HotReload`` here is not a first-class Document.use product API.

See ``docs/internals/SYSTEM.md`` and ux-compose ``docs/FLOW.md``.
"""

from ux_dom.plugins import protocols as protocols
from ux_dom.plugins.contribution import StaticArtifact
from ux_dom.plugins.csp import (
    policy_report_only,
    policy_prod,
    policy_dev,
    CspPolicy,
    Csp,
    CspMiddleware,
    CspNonce,
    build_csp_header,
    generate_nonce,
    get_nonce,
    resolve_nonce,
    shell_fragments_nonced,
    stamp_nonce,
    stamp_tree,
)
from ux_dom.plugins.dedupe import dedupe_dom_nodes, extract_script_srcs
from ux_dom.plugins.hub import App, PluginHub, get_hub, set_hub
from ux_dom.plugins.package_static import (
    PackageStaticContribution,
    PackagedFile,
    static_from_package,
    ux_channel_static,
)
from ux_dom.plugins.runtime import UxChannelRuntime, XElementRuntime
from ux_dom.plugins.shell import runtime_tags, shell_fragments

__all__ = [
    "App",
    "PluginHub",
    "get_hub",
    "set_hub",
    "runtime_tags",
    "shell_fragments",
    "XElementRuntime",
    "UxChannelRuntime",
    "Csp",
    "policy_report_only",
    "policy_prod",
    "policy_dev",
    "CspPolicy",
    "CspNonce",
    "CspMiddleware",
    "StaticArtifact",
    "PackageStaticContribution",
    "PackagedFile",
    "static_from_package",
    "ux_channel_static",
    "get_nonce",
    "resolve_nonce",
    "stamp_nonce",
    "stamp_tree",
    "generate_nonce",
    "build_csp_header",
    "shell_fragments_nonced",
    "dedupe_dom_nodes",
    "extract_script_srcs",
    "protocols",
]
