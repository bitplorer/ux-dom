# Copyright (c) 2026 ux-dom
"""Registry of ux-dom UI kit components (for CLI + docs + doctor)."""

from __future__ import annotations

from typing import TypedDict


class UiEntry(TypedDict):
    name: str
    module: str
    exports: list[str]
    description: str
    channel: bool


# name → metadata (module path relative to ux_dom.ui)
CATALOG: dict[str, UiEntry] = {
    "button": {
        "name": "Button",
        "module": "ux_dom.ui.button",
        "exports": ["Button", "button_classes"],
        "description": "Primary actions — variants default/secondary/outline/ghost/destructive/link",
        "channel": False,
    },
    "input": {
        "name": "Input",
        "module": "ux_dom.ui.input",
        "exports": ["Input", "input_classes"],
        "description": "Text field",
        "channel": False,
    },
    "textarea": {
        "name": "Textarea",
        "module": "ux_dom.ui.textarea",
        "exports": ["Textarea"],
        "description": "Multiline text",
        "channel": False,
    },
    "label": {
        "name": "Label",
        "module": "ux_dom.ui.label",
        "exports": ["Label"],
        "description": "Form label",
        "channel": False,
    },
    "card": {
        "name": "Card",
        "module": "ux_dom.ui.card",
        "exports": [
            "Card",
            "CardHeader",
            "CardTitle",
            "CardDescription",
            "CardContent",
            "CardFooter",
        ],
        "description": "Surface container (shadcn Card anatomy)",
        "channel": False,
    },
    "badge": {
        "name": "Badge",
        "module": "ux_dom.ui.badge",
        "exports": ["Badge"],
        "description": "Status chip",
        "channel": False,
    },
    "alert": {
        "name": "Alert",
        "module": "ux_dom.ui.alert",
        "exports": ["Alert", "AlertTitle", "AlertDescription"],
        "description": "Inline feedback",
        "channel": False,
    },
    "separator": {
        "name": "Separator",
        "module": "ux_dom.ui.separator",
        "exports": ["Separator"],
        "description": "Horizontal/vertical rule",
        "channel": False,
    },
    "skeleton": {
        "name": "Skeleton",
        "module": "ux_dom.ui.skeleton",
        "exports": ["Skeleton"],
        "description": "Loading placeholder",
        "channel": False,
    },
    "avatar": {
        "name": "Avatar",
        "module": "ux_dom.ui.avatar",
        "exports": ["Avatar", "AvatarImage", "AvatarFallback"],
        "description": "User image + fallback",
        "channel": False,
    },
    "checkbox": {
        "name": "Checkbox",
        "module": "ux_dom.ui.checkbox",
        "exports": ["Checkbox"],
        "description": "Boolean input",
        "channel": False,
    },
    "switch": {
        "name": "Switch",
        "module": "ux_dom.ui.switch",
        "exports": ["Switch"],
        "description": "Toggle switch",
        "channel": False,
    },
    "select": {
        "name": "Select",
        "module": "ux_dom.ui.select",
        "exports": ["Select"],
        "description": "Native select styled",
        "channel": False,
    },
    "slider": {
        "name": "Slider",
        "module": "ux_dom.ui.slider",
        "exports": ["Slider", "slider_classes"],
        "description": "Native range input",
        "channel": False,
    },
    "table": {
        "name": "Table",
        "module": "ux_dom.ui.table",
        "exports": [
            "Table",
            "TableHeader",
            "TableBody",
            "TableRow",
            "TableHead",
            "TableCell",
            "TableCaption",
            "TableEmpty",
        ],
        "description": "Data table primitives + empty state",
        "channel": False,
    },
    "tabs": {
        "name": "Tabs",
        "module": "ux_dom.ui.tabs",
        "exports": ["Tabs"],
        "description": "Alpine tabs",
        "channel": False,
    },
    "dialog": {
        "name": "Dialog",
        "module": "ux_dom.ui.dialog",
        "exports": ["Dialog"],
        "description": "Alpine modal dialog",
        "channel": False,
    },
    "carousel": {
        "name": "Carousel",
        "module": "ux_dom.ui.carousel",
        "exports": ["Carousel"],
        "description": "Alpine slide carousel (empty state included)",
        "channel": False,
    },
    "toast": {
        "name": "Toast",
        "module": "ux_dom.ui.toast",
        "exports": ["ToastHost", "ToastItem"],
        "description": "Morph-safe notices host — server list is authority",
        "channel": False,
    },
    "datepicker": {
        "name": "DatePicker",
        "module": "ux_dom.ui.datepicker",
        "exports": ["DatePicker"],
        "description": "Native date input",
        "channel": False,
    },
    "chart": {
        "name": "Chart",
        "module": "ux_dom.ui.chart",
        "exports": ["Chart"],
        "description": "SVG sparkline / bar shell (no Chart.js)",
        "channel": False,
    },
    "channel_bridge": {
        "name": "ChannelBridge",
        "module": "ux_dom.ui.channel_bridge",
        "exports": [
            "channel_available",
            "stamp_region",
            "action_button_attrs",
            "to_fragment",
            "live_button",
            "public_form",
        ],
        "description": "Optional ux-channel morph/action helpers + progressive form",
        "channel": True,
    },
}

# Local runtime required for interactive chrome. None = pure server HTML.
# Doctor (ux-app ui_health) fails production apps that use a composite
# without declaring the matching Document.use plugin.
RUNTIMES: dict[str, str | None] = {
    "button": None,
    "input": None,
    "textarea": None,
    "label": None,
    "card": None,
    "badge": None,
    "alert": None,
    "separator": None,
    "skeleton": None,
    "avatar": None,
    "checkbox": None,
    "switch": None,
    "select": None,
    "slider": None,
    "table": None,
    "tabs": "alpine",
    "dialog": "alpine",
    "carousel": "alpine",
    "toast": None,
    "datepicker": None,
    "chart": None,
    "channel_bridge": None,
}


def list_components(*, channel: bool | None = None) -> list[UiEntry]:
    items = list(CATALOG.values())
    if channel is None:
        return items
    return [i for i in items if i["channel"] is channel]


def runtime_for(name: str) -> str | None:
    return RUNTIMES.get(name.strip().lower())
