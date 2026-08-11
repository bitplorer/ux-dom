"""Complex CustomElement / WebComponent / AlpineComponent — auth & multi-host.

Covers definition rules, registry SSoT, Document auto-collection, multi-instance
hosts, shadow vs light constraints, and login/signup component structure.
"""
from __future__ import annotations

import unittest
from concurrent.futures import ThreadPoolExecutor

from ux_dom import Document
from ux_dom.dom import div, span
from ux_dom.dom.htmlelement import (
    CustomElement,
    WebComponent,
    XElement,
    xelement_registry,
)

from tests.fixtures.auth_xelements import (
    AuthShell,
    LoginForm,
    ProfileBadge,
    SessionBanner,
    SignupForm,
)


class TestAuthCustomElementDefinitions(unittest.TestCase):
    def setUp(self):
        xelement_registry.clear()

    def test_login_host_and_single_definition(self):
        hosts = [LoginForm(), LoginForm(), LoginForm()]
        for h in hosts:
            self.assertEqual(h.tagname, "x-login-form")
        d1 = LoginForm.definition()
        d2 = LoginForm.definition()
        self.assertIs(d1, d2)
        html = str(d1)
        self.assertIn('x-tagname="login-form"', html)
        self.assertIn("x-data", html)
        self.assertIn("Sign in", html)
        self.assertNotIn("shadowroot", html)

    def test_signup_definition_fields(self):
        d = SignupForm.definition()
        html = str(d)
        self.assertIn('x-tagname="signup-form"', html)
        for name in ("name", "email", "password", "confirm"):
            self.assertIn(f'name="{name}"', html)
        self.assertIn("Create account", html)

    def test_auth_shell_requires_shadow(self):
        d = AuthShell.definition()
        html = str(d)
        self.assertIn('x-tagname="auth-shell"', html)
        self.assertIn("shadowroot", html)
        self.assertIn("<slot", html)

    def test_document_auto_collects_one_template_per_tag(self):
        doc = Document(head=[], body=[], ensure_csrf_token=False)
        page = div(
            LoginForm(),
            LoginForm(),
            SignupForm(),
            AuthShell(span("body slot"), **{"slot": "nope"}) if False else AuthShell(),
            ProfileBadge(),
            ProfileBadge(),
            SessionBanner(),
        )
        # AuthShell with light children
        shell = AuthShell(div(LoginForm(), id="inside-shell"))
        html = str(doc(div(page, shell, id="app")))
        self.assertEqual(html.count('x-tagname="login-form"'), 1)
        self.assertEqual(html.count('x-tagname="signup-form"'), 1)
        self.assertEqual(html.count('x-tagname="auth-shell"'), 1)
        self.assertEqual(html.count('x-tagname="profile-badge"'), 1)
        self.assertGreaterEqual(html.count("<x-login-form"), 2)
        self.assertGreaterEqual(html.count("<x-profile-badge"), 2)
        self.assertIn("<x-auth-shell", html)

    def test_cannot_construct_xelement_base(self):
        with self.assertRaises(TypeError):
            XElement()


class TestCustomElementConstraints(unittest.TestCase):
    def setUp(self):
        xelement_registry.clear()

    def test_custom_element_rejects_shadow(self):
        class BadLight(CustomElement):
            tag_name = "bad-light"

            def render(self, tag_name: str = "bad-light"):
                from ux_dom.dom import template

                return template(
                    div("x"),
                    **{"x-tagname": tag_name, "shadowroot": "true"},
                )

        with self.assertRaises(AttributeError):
            BadLight.definition()

    def test_web_component_requires_shadow(self):
        class BadShadow(WebComponent):
            tag_name = "bad-shadow"

            def render(self, tag_name: str = "bad-shadow"):
                from ux_dom.dom import template

                return template(div("x"), **{"x-tagname": tag_name})

        with self.assertRaises(AttributeError):
            BadShadow.definition()

    def test_missing_xtagname_fails(self):
        class NoTag(CustomElement):
            tag_name = "no-tag"

            def render(self, tag_name: str = "no-tag"):
                return div("no template")

        with self.assertRaises(AttributeError):
            NoTag.definition()


class TestMultiInstanceStress(unittest.TestCase):
    def setUp(self):
        xelement_registry.clear()

    def test_fifty_badges_one_definition(self):
        doc = Document(head=[], body=[], ensure_csrf_token=False)
        hosts = [ProfileBadge() for _ in range(50)]
        html = str(doc(div(*hosts)))
        self.assertEqual(html.count('x-tagname="profile-badge"'), 1)
        self.assertEqual(html.count("<x-profile-badge"), 50)

    def test_parallel_definition_idempotent(self):
        def work(_):
            LoginForm()
            return id(LoginForm.definition())

        with ThreadPoolExecutor(8) as ex:
            ids = list(ex.map(work, range(40)))
        # all same definition object id
        self.assertEqual(len(set(ids)), 1)


class TestAuthComposition(unittest.TestCase):
    def setUp(self):
        xelement_registry.clear()

    def test_login_and_signup_side_by_side_markup(self):
        doc = Document(head=[], body=[], ensure_csrf_token=False)
        html = str(
            doc(
                div(
                    LoginForm(),
                    SignupForm(),
                    className="grid gap-4 md:grid-cols-2",
                    id="auth-grid",
                )
            )
        )
        self.assertIn('id="auth-grid"', html)
        self.assertIn("<x-login-form", html)
        self.assertIn("<x-signup-form", html)
        self.assertIn("data-testid", html)  # from definition template body
        # definition templates present once each
        self.assertEqual(html.count('x-tagname="login-form"'), 1)
        self.assertEqual(html.count('x-tagname="signup-form"'), 1)

    def test_shell_wraps_login_host(self):
        doc = Document(head=[], body=[], ensure_csrf_token=False)
        html = str(doc(AuthShell(LoginForm(), **{})))
        self.assertIn("<x-auth-shell", html)
        self.assertIn("<x-login-form", html)
        self.assertIn('x-tagname="auth-shell"', html)


if __name__ == "__main__":
    unittest.main()
