"""Gallery of ux_dom.ui components."""
from __future__ import annotations

from ux_dom import Component
from ux_dom.dom import a, div, h1, h2, p, span
from ux_dom.ui import (
    Alert,
    AlertDescription,
    AlertTitle,
    Avatar,
    AvatarFallback,
    Badge,
    Button,
    Card,
    CardContent,
    CardDescription,
    CardFooter,
    CardHeader,
    CardTitle,
    Checkbox,
    Dialog,
    Input,
    Label,
    Select,
    Separator,
    Skeleton,
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
    Tabs,
    Textarea,
)
from ux_dom.ui.channel_bridge import channel_available, live_button, stamp_region

from app.document import page

__all__ = ["Index"]


class Index(Component):
    routes = ["get"]

    def render(self):
        ch = channel_available()
        live = live_button(
            "Live action (needs channel)",
            action="Demo.ping",
            variant="secondary",
            size="sm",
        )
        region = stamp_region(
            Card(
                CardHeader(CardTitle("Morph region"), CardDescription("data-channel-id stamped")),
                CardContent(p("Target for uxchannel morph when bridge is live.")),
            ),
            uid="Gallery:card",
        )

        return div(
            div(
                h1("UxDom UI kit", className="text-3xl font-bold tracking-tight"),
                p(
                    "Shadcn-inspired components — pure Python HTML + Tailwind. "
                    f"ux-channel: {'available' if ch else 'not installed (optional)'}.",
                    className="text-slate-600 mt-2 text-sm",
                ),
                className="mb-10",
            ),
            # Buttons
            section("Buttons", div(
                Button("Default"),
                Button("Secondary", variant="secondary"),
                Button("Outline", variant="outline"),
                Button("Ghost", variant="ghost"),
                Button("Destructive", variant="destructive"),
                Button("Link", variant="link"),
                Button("Small", size="sm", variant="outline"),
                className="flex flex-wrap gap-2",
            )),
            # Form
            section("Form controls", div(
                div(Label("Email"), Input(type="email", placeholder="you@example.com", className="mt-1.5"), className="max-w-sm"),
                div(Label("Plan"), Select(options=[("free", "Free"), ("pro", "Pro")], className="mt-1.5 max-w-sm"), className="mt-4"),
                div(Label("Bio"), Textarea(placeholder="About you", className="mt-1.5 max-w-sm"), className="mt-4"),
                div(Checkbox(id="tos"), Label(" Accept terms", **{"for": "tos"}), className="mt-4 flex items-center gap-2"),
            )),
            # Card + Badge + Alert
            section("Surfaces", div(
                Card(
                    CardHeader(
                        CardTitle("Project"),
                        CardDescription("Deploy your new project in one click."),
                    ),
                    CardContent(
                        div(Badge("stable"), Badge("ui", variant="secondary"), className="flex gap-2"),
                    ),
                    CardFooter(Button("Deploy", size="sm")),
                    className="max-w-md",
                ),
                Alert(
                    AlertTitle("Heads up"),
                    AlertDescription("You can use HTMX attrs on any Button/Input."),
                    className="mt-4 max-w-md",
                    variant="default",
                ),
                Alert(
                    AlertTitle("Error"),
                    AlertDescription("Something went wrong."),
                    variant="destructive",
                    className="mt-2 max-w-md",
                ),
            )),
            section("Table", Table(
                TableHeader(TableRow(TableHead("Name"), TableHead("Status"), TableHead("Role"))),
                TableBody(
                    TableRow(TableCell("Ada"), TableCell(Badge("active", variant="success")), TableCell("Admin")),
                    TableRow(TableCell("Lin"), TableCell(Badge("trial", variant="secondary")), TableCell("Member")),
                ),
                className="max-w-lg",
            )),
            section("Tabs (Alpine)", Tabs(
                items=[
                    ("a", "Account", p("Make changes to your account here.")),
                    ("b", "Password", p("Change your password here.")),
                ],
            )),
            section("Dialog (Alpine)", Dialog(
                trigger=Button("Open dialog", variant="outline"),
                title="Edit profile",
                body=p("This is a lightweight Alpine modal — no React."),
                footer=Button("Save", size="sm"),
            )),
            section("Avatar / Skeleton / Separator", div(
                Avatar(AvatarFallback("SA")),
                Separator(className="my-4"),
                Skeleton(className="h-4 w-48"),
                className="max-w-sm",
            )),
            section("Channel bridge", div(
                p(
                    "stamp_region + live_button work without channel (attrs stubbed); "
                    "with uxchannel installed they carry signed caps / morph targets.",
                    className="text-sm text-slate-600 mb-3 max-w-xl",
                ),
                live,
                div(region, className="mt-4 max-w-md"),
            )),
            className="max-w-3xl mx-auto px-4 py-12",
        )

    @classmethod
    def get(cls):
        return page(cls(), page_title="UI Kit · UxDom")


def section(title: str, body):
    return div(
        h2(title, className="text-lg font-semibold mb-3 mt-10"),
        body,
    )
