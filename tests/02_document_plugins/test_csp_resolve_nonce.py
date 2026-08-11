"""Read-agnostic secure CSP nonce."""

from __future__ import annotations

import unittest

from ux_dom.dom import div, script
from ux_dom.plugins.csp import (
    bind_nonce_to_scope,
    clear_nonce,
    generate_nonce,
    get_nonce,
    reset_nonce,
    resolve_nonce,
    set_nonce,
    stamp_tree,
)


class TestSecureNonce(unittest.TestCase):
    def tearDown(self):
        clear_nonce()

    def test_entropy(self):
        a, b = generate_nonce(), generate_nonce()
        self.assertNotEqual(a, b)
        self.assertGreaterEqual(len(a), 32)

    def test_resolve_explicit_wins(self):
        tok = set_nonce("from-context")
        try:
            self.assertEqual(resolve_nonce("explicit"), "explicit")
            self.assertEqual(resolve_nonce(), "from-context")
        finally:
            reset_nonce(tok)

    def test_resolve_from_scope(self):
        clear_nonce()
        scope = {"type": "http", "ux_dom_csp_nonce": "from-scope"}
        self.assertEqual(resolve_nonce(scope=scope), "from-scope")

    def test_bind_and_resolve(self):
        clear_nonce()
        scope: dict = {"type": "http", "state": {}}
        bind_nonce_to_scope(scope, "bound")
        self.assertEqual(resolve_nonce(scope=scope), "bound")
        self.assertEqual(scope["state"]["ux_dom_csp_nonce"], "bound")

    def test_stamp_bakes_read_agnostic(self):
        """After stamp with explicit n, tree needs no ContextVar to serialize."""
        tree = div(script("alert(1)"))
        stamp_tree(tree, "baked-nonce-xyz")
        clear_nonce()
        html = tree.__render__(pretty=False)
        self.assertIn('nonce="baked-nonce-xyz"', html)
        self.assertEqual(resolve_nonce(), "")

    def test_require_raises(self):
        clear_nonce()
        with self.assertRaises(RuntimeError):
            resolve_nonce(require=True)


if __name__ == "__main__":
    unittest.main()
