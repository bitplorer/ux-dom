"""Complex CustomElement / WebComponent / AlpineComponent fixtures (auth flows).

Used by unit + live browser suites. Mirrors real multi-step login/signup UX:

* ``LoginForm`` — AlpineComponent light CE with validation + success state
* ``SignupForm`` — AlpineComponent with multi-field validation + password match
* ``AuthShell`` — WebComponent shadow chrome with named slots
* ``ProfileBadge`` — CustomElement light badge (multi-instance stress)
* ``SessionBanner`` — CustomElement showing session state from light attrs
"""
from __future__ import annotations

from dataclasses import dataclass

from ux_dom.dom import (
    button,
    div,
    form,
    h2,
    input_,
    label,
    p,
    slot,
    span,
    template,
)
from ux_dom.dom.htmlelement import AlpineComponent, CustomElement, WebComponent

__all__ = [
    "LoginForm",
    "SignupForm",
    "AuthShell",
    "ProfileBadge",
    "SessionBanner",
    "AUTH_LOGIN_XDATA",
    "AUTH_SIGNUP_XDATA",
]

# Alpine state objects as plain strings (kept readable; HTML attr escape is fine
# because browsers decode entities when scripts read attributes).
AUTH_LOGIN_XDATA = """{
  email: '',
  password: '',
  error: '',
  ok: false,
  attempts: 0,
  login() {
    this.attempts += 1;
    this.error = '';
    this.ok = false;
    if (!this.email || !this.password) {
      this.error = 'Email and password are required';
      return;
    }
    if (this.password.length <= 3) {
      this.error = 'Password too short';
      return;
    }
    if (this.email.indexOf('@') === -1) {
      this.error = 'Invalid email';
      return;
    }
    this.ok = true;
  }
}"""

AUTH_SIGNUP_XDATA = """{
  name: '',
  email: '',
  password: '',
  confirm: '',
  error: '',
  ok: false,
  signup() {
    this.error = '';
    this.ok = false;
    if (!this.name || !this.email || !this.password || !this.confirm) {
      this.error = 'All fields are required';
      return;
    }
    if (this.password.length <= 5) {
      this.error = 'Password must be at least 6 characters';
      return;
    }
    if (this.password !== this.confirm) {
      this.error = 'Passwords do not match';
      return;
    }
    if (this.email.indexOf('@') === -1) {
      this.error = 'Invalid email';
      return;
    }
    this.ok = true;
  }
}"""


def _field(label_text: str, *, name: str, type_: str = "text", model: str):
    return div(
        label(label_text, className="block text-xs font-medium text-slate-600 mb-1"),
        input_(
            type=type_,
            name=name,
            autocomplete=name,
            className=(
                "w-full rounded-md border border-slate-300 px-3 py-2 text-sm "
                "focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500"
            ),
            **{"x-model": model},
        ),
        className="mb-3",
    )


@dataclass(eq=False)
class LoginForm(AlpineComponent):
    """Login custom element (Alpine + XElement light DOM)."""

    tag_name = "login-form"

    def render(self, tag_name: str = "login-form"):
        return template(
            div(
                h2("Sign in", className="text-lg font-semibold mb-3"),
                form(
                    _field("Email", name="email", type_="email", model="email"),
                    _field(
                        "Password", name="password", type_="password", model="password"
                    ),
                    button(
                        "Sign in",
                        type="submit",
                        className=(
                            "w-full rounded-md bg-sky-600 px-3 py-2 text-sm "
                            "font-medium text-white hover:bg-sky-700"
                        ),
                        id="login-submit",
                    ),
                    p(
                        className="mt-2 text-sm text-rose-600",
                        **{
                            "x-text": "error",
                            "x-show": "error",
                            "data-testid": "login-error",
                        },
                    ),
                    p(
                        "Signed in successfully",
                        className="mt-2 text-sm text-emerald-600 font-medium",
                        **{
                            "x-show": "ok",
                            "data-testid": "login-ok",
                        },
                    ),
                    span(
                        className="sr-only",
                        **{"x-text": "attempts", "data-testid": "login-attempts"},
                    ),
                    **{"@submit.prevent": "login()", "data-testid": "login-form"},
                ),
                className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm",
                **{"x-data": AUTH_LOGIN_XDATA, "data-auth": "login"},
            ),
            **{"x-tagname": tag_name},
        )


@dataclass(eq=False)
class SignupForm(AlpineComponent):
    """Signup custom element with multi-field validation."""

    tag_name = "signup-form"

    def render(self, tag_name: str = "signup-form"):
        return template(
            div(
                h2("Create account", className="text-lg font-semibold mb-3"),
                form(
                    _field("Name", name="name", model="name"),
                    _field("Email", name="email", type_="email", model="email"),
                    _field(
                        "Password", name="password", type_="password", model="password"
                    ),
                    _field(
                        "Confirm password",
                        name="confirm",
                        type_="password",
                        model="confirm",
                    ),
                    button(
                        "Sign up",
                        type="submit",
                        className=(
                            "w-full rounded-md bg-emerald-600 px-3 py-2 text-sm "
                            "font-medium text-white hover:bg-emerald-700"
                        ),
                        id="signup-submit",
                    ),
                    p(
                        className="mt-2 text-sm text-rose-600",
                        **{
                            "x-text": "error",
                            "x-show": "error",
                            "data-testid": "signup-error",
                        },
                    ),
                    p(
                        "Account created",
                        className="mt-2 text-sm text-emerald-600 font-medium",
                        **{"x-show": "ok", "data-testid": "signup-ok"},
                    ),
                    **{"@submit.prevent": "signup()", "data-testid": "signup-form"},
                ),
                className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm",
                **{"x-data": AUTH_SIGNUP_XDATA, "data-auth": "signup"},
            ),
            **{"x-tagname": tag_name},
        )


@dataclass(eq=False)
class AuthShell(WebComponent):
    """Shadow chrome for auth pages — header + default body slot."""

    tag_name = "auth-shell"

    def render(self, tag_name: str = "auth-shell"):
        return template(
            div(
                div(
                    slot(name="header"),
                    className="border-b border-slate-700 px-4 py-2 text-xs uppercase tracking-wide text-slate-400",
                ),
                div(slot(), className="p-4"),
                className="rounded-2xl bg-slate-900 text-slate-100 shadow-xl overflow-hidden",
                **{"data-dom": "shadow"},
            ),
            **{"x-tagname": tag_name, "shadowroot": "true"},
        )


@dataclass(eq=False)
class ProfileBadge(CustomElement):
    """Light-DOM badge — many instances share one definition."""

    tag_name = "profile-badge"

    def render(self, tag_name: str = "profile-badge"):
        return template(
            span(
                "● online",
                className=(
                    "inline-flex items-center gap-1 rounded-full bg-emerald-50 "
                    "px-2 py-0.1 text-xs font-medium text-emerald-700 ring-1 "
                    "ring-emerald-200"
                ),
                **{"data-dom": "light"},
            ),
            **{"x-tagname": tag_name},
        )


@dataclass(eq=False)
class SessionBanner(CustomElement):
    """Light banner; host may carry data-user for display after upgrade."""

    tag_name = "session-banner"

    def render(self, tag_name: str = "session-banner"):
        return template(
            div(
                span("Session: ", className="opacity-70"),
                span(
                    "guest",
                    className="font-semibold",
                    **{"data-testid": "session-user"},
                ),
                className=(
                    "rounded-md border border-amber-200 bg-amber-50 px-3 py-2 "
                    "text-sm text-amber-900"
                ),
                **{"data-dom": "light"},
            ),
            **{"x-tagname": tag_name},
        )
