# Copyright (c) 2026 ux-dom
"""
ux-dom UI kit — Channel-first, shadcn-inspired (optional, Tailwind utilities).

Ownership: markup + tokens only. No Op construction. No ux_behavior / ux_app imports.

Pure server HTML. Works **without** ux-channel. For live morph / signed actions::

    from ux_dom.ui.channel_bridge import stamp_region, live_button, channel_available

Copy into your app (ownable like shadcn)::

    uxdom add ui Button
    uxdom ui list
"""

from __future__ import annotations

from ux_dom.ui.alert import Alert, AlertDescription, AlertTitle
from ux_dom.ui.avatar import Avatar, AvatarFallback, AvatarImage
from ux_dom.ui.badge import Badge
from ux_dom.ui.breadcrumb import Breadcrumb
from ux_dom.ui.button import Button, button_classes
from ux_dom.ui.card import (
    Card,
    CardContent,
    CardDescription,
    CardFooter,
    CardHeader,
    CardTitle,
)
from ux_dom.ui.carousel import Carousel
from ux_dom.ui.chart import Chart
from ux_dom.ui.checkbox import Checkbox
from ux_dom.ui.command import Command
from ux_dom.ui.datepicker import DatePicker
from ux_dom.ui.dialog import Dialog
from ux_dom.ui.dropdown_menu import DropdownMenu
from ux_dom.ui.empty_state import EmptyState
from ux_dom.ui.form_section import FormSection
from ux_dom.ui.input import Input, input_classes
from ux_dom.ui.kbd import Kbd
from ux_dom.ui.label import Label
from ux_dom.ui.page_header import PageHeader
from ux_dom.ui.pagination import Pagination
from ux_dom.ui.popover import Popover
from ux_dom.ui.progress import Progress
from ux_dom.ui.radio_group import RadioGroup
from ux_dom.ui.select import Select
from ux_dom.ui.separator import Separator
from ux_dom.ui.sheet import Sheet
from ux_dom.ui.skeleton import Skeleton
from ux_dom.ui.slider import Slider, slider_classes
from ux_dom.ui.status_strip import StatusStrip
from ux_dom.ui.switch import Switch
from ux_dom.ui.table import (
    Table,
    TableBody,
    TableCaption,
    TableCell,
    TableEmpty,
    TableHead,
    TableHeader,
    TableRow,
)
from ux_dom.ui.tabs import Tabs
from ux_dom.ui.textarea import Textarea, textarea_classes
from ux_dom.ui.toast import ToastHost, ToastItem
from ux_dom.ui.tokens import (
    cn,
    color,
    density,
    field_classes,
    focus_ring,
    ink,
    overlay,
    radius,
    surface,
    target,
    type_scale,
    variants,
)

__all__ = [
    "cn",
    "variants",
    "focus_ring",
    "radius",
    "surface",
    "ink",
    "type_scale",
    "target",
    "density",
    "overlay",
    "color",
    "field_classes",
    "Button",
    "button_classes",
    "Input",
    "input_classes",
    "Textarea",
    "textarea_classes",
    "Label",
    "Card",
    "CardHeader",
    "CardTitle",
    "CardDescription",
    "CardContent",
    "CardFooter",
    "Badge",
    "Alert",
    "AlertTitle",
    "AlertDescription",
    "Separator",
    "Skeleton",
    "Checkbox",
    "Switch",
    "Select",
    "Slider",
    "slider_classes",
    "RadioGroup",
    "Progress",
    "Avatar",
    "AvatarImage",
    "AvatarFallback",
    "Table",
    "TableHeader",
    "TableBody",
    "TableRow",
    "TableHead",
    "TableCell",
    "TableCaption",
    "TableEmpty",
    "Tabs",
    "Dialog",
    "Sheet",
    "ToastHost",
    "ToastItem",
    "Breadcrumb",
    "Pagination",
    "DatePicker",
    "Kbd",
    "Carousel",
    "Command",
    "Popover",
    "DropdownMenu",
    "EmptyState",
    "PageHeader",
    "StatusStrip",
    "FormSection",
    "Chart",
]
