"""Gallery page: one section per ``ux_dom.ui`` component family.

Interactive components (Tabs, Carousel, Dialog) take their state as render
arguments. The gallery reads that state from the query string and changes it
with ordinary links, so it works without JavaScript.
"""

from __future__ import annotations

from datetime import datetime

from ux_dom.dom import a, div, h1, h2, p
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
    Carousel,
    Chart,
    Checkbox,
    DatePicker,
    Dialog,
    Input,
    Label,
    Select,
    Separator,
    Skeleton,
    Slider,
    Switch,
    Table,
    TableBody,
    TableCell,
    TableEmpty,
    TableHead,
    TableHeader,
    TableRow,
    Tabs,
    Textarea,
    ToastHost,
)

from .document import page

TABS = (
    ("a", "Account", p("Make changes to your account here.")),
    ("b", "Password", p("Change your password here.")),
)
SLIDES = (
    p("Slide one: the index is a render argument."),
    p("Slide two: the server picks the slide."),
)
LINK = "text-sm text-sky-400 underline"


def section(title: str, *body):
    return div(h2(title, className="text-lg font-semibold mb-3 mt-10"), *body)


def buttons():
    return div(
        Button("Default"),
        Button("Secondary", variant="secondary"),
        Button("Outline", variant="outline"),
        Button("Ghost", variant="ghost"),
        Button("Destructive", variant="destructive"),
        Button("Link", variant="link"),
        Button("Small", size="sm", variant="outline"),
        className="flex flex-wrap gap-2",
    )


def form_controls():
    def field(label_text, control, extra=""):
        return div(Label(label_text), control, className=f"mt-4 max-w-sm {extra}")

    return div(
        field("Email", Input(type="email", placeholder="you@example.com")),
        field("Plan", Select(options=[("free", "Free"), ("pro", "Pro")])),
        field("Bio", Textarea(placeholder="About you")),
        div(
            Checkbox(id="tos"),
            Label(" Accept terms", **{"for": "tos"}),
            className="mt-4 flex items-center gap-2",
        ),
        field("Alerts", Switch(checked=True)),
        field("Volume", Slider(name="vol", value=40, show_value=True)),
        field("Due", DatePicker(name="due", value="2026-08-16")),
    )


def surfaces():
    return div(
        Card(
            CardHeader(
                CardTitle("Project"),
                CardDescription("Deploy your new project in one click."),
            ),
            CardContent(
                div(
                    Badge("stable"),
                    Badge("ui", variant="secondary"),
                    className="flex gap-2",
                )
            ),
            CardFooter(Button("Deploy", size="sm")),
            className="max-w-md",
        ),
        Alert(
            AlertTitle("Heads up"),
            AlertDescription("Button and Input pass hx-* attributes through."),
            className="mt-4 max-w-md",
        ),
        Alert(
            AlertTitle("Error"),
            AlertDescription("Something went wrong."),
            variant="destructive",
            className="mt-2 max-w-md",
        ),
    )


def table():
    return Table(
        TableHeader(
            TableRow(TableHead("Name"), TableHead("Status"), TableHead("Role"))
        ),
        TableBody(
            TableRow(
                TableCell("Ada"),
                TableCell(Badge("active", variant="success")),
                TableCell("Admin"),
            ),
            TableRow(
                TableCell("Lin"),
                TableCell(Badge("trial", variant="secondary")),
                TableCell("Member"),
            ),
            TableEmpty("Empty-state row ships with the kit", col_span=3),
        ),
        className="max-w-lg",
    )


def tabs(active: str):
    links = [
        a(f"Show {label}", href=f"/?tab={key}", className=LINK)
        for key, label, _ in TABS
    ]
    return div(
        Tabs(items=list(TABS), active=active), div(*links, className="mt-2 flex gap-4")
    )


def carousel(index: int):
    links = [
        a(f"Slide {i + 1}", href=f"/?slide={i}", className=LINK)
        for i in range(len(SLIDES))
    ]
    return div(
        Carousel(slides=list(SLIDES), label="Highlights", index=index),
        div(*links, className="mt-2 flex gap-4"),
    )


def dialog(is_open: bool):
    return div(
        a("Open the dialog", href="/?dialog=1", className=LINK),
        Dialog(
            open=is_open,
            title="Edit profile",
            body=p("Open state is a render argument; this link set it."),
            footer=a("Close", href="/", className=LINK),
        ),
    )


def toasts(items=()):
    return div(
        Button(
            "Save (htmx)",
            size="sm",
            hx_post="/toast",
            hx_target="#toasts",
            hx_swap="outerHTML",
        ),
        ToastHost(items=list(items), id="toasts", className="mt-3"),
    )


def toast_fragment():
    """``POST /toast``: the new ToastHost htmx swaps in."""
    text = f"Saved at {datetime.now():%H:%M:%S}"
    return ToastHost(
        items=[{"text": text, "level": "success"}], id="toasts", className="mt-3"
    )


def get(tab: str = "a", slide: int = 0, dialog_open: bool = False):
    return page(
        div(
            div(
                h1("UxDom UI kit", className="text-3xl font-bold tracking-tight"),
                p(
                    "Shadcn-inspired components: server-rendered HTML,"
                    " styled with Tailwind classes.",
                    className="text-stone-400 mt-2 text-sm",
                ),
                section("Buttons", buttons()),
                section("Form controls", form_controls()),
                section("Surfaces", surfaces()),
                section("Table", table()),
                section("Tabs", tabs(tab)),
                section("Dialog", dialog(dialog_open)),
                section("Carousel", carousel(slide)),
                section("Toast", toasts()),
                section(
                    "Chart (SVG)", Chart(series=[4, 8, 6, 12, 9, 14], label="Revenue")
                ),
                section(
                    "Avatar / Skeleton / Separator",
                    div(
                        Avatar(AvatarFallback("SA")),
                        Separator(className="my-4"),
                        Skeleton(className="h-4 w-48"),
                        className="max-w-sm",
                    ),
                ),
                className="max-w-3xl mx-auto px-4 py-12",
            ),
            className="min-h-screen bg-stone-950 text-stone-100 antialiased",
        )
    )
