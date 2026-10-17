"""Gate for tests that need the ux-channel companion package.

Locally they skip when ux-channel is absent. CI installs a pinned ux-channel
and sets ``UX_DOM_REQUIRE_CHANNEL=1`` so a missing package fails instead of
skipping: an integration gate that can silently skip is not a gate.
"""

from __future__ import annotations

import importlib.util
import os
import unittest

HINT = (
    'pip install "ux-channel @ git+https://github.com/bitplorer/ux-channel.git'
    '@f1a93fcf298c97a59fa6538697731e19aac8586d#subdirectory=python"'
)


def require_channel() -> None:
    if importlib.util.find_spec("ux_channel") is not None:
        return
    if os.environ.get("UX_DOM_REQUIRE_CHANNEL") == "1":
        raise AssertionError(
            f"UX_DOM_REQUIRE_CHANNEL=1 but ux-channel is missing; run: {HINT}"
        )
    raise unittest.SkipTest(f"ux-channel not installed; run: {HINT}")
