# Copyright (c) 2026 ux-dom
"""
ux-dom UI kit — shadcn-inspired components (optional, Tailwind utility classes).

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
from ux_dom.ui.datepicker import DatePicker
from ux_dom.ui.dialog import Dialog
from ux_dom.ui.input import Input, input_classes
from ux_dom.ui.label import Label
from ux_dom.ui.select import Select
from ux_dom.ui.separator import Separator
from ux_dom.ui.skeleton import Skeleton
from ux_dom.ui.slider import Slider, slider_classes
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
from ux_dom.ui.textarea import Textarea
from ux_dom.ui.toast import ToastHost, ToastItem
from ux_dom.ui.tokens import cn, focus_ring, radius, variants

__all__ = [
    "cn",
    "variants",
    "focus_ring",
    "radius",
    "Button",
    "button_classes",
    "Input",
    "input_classes",
    "Textarea",
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
    "Avatar",
    "AvatarImage",
    "AvatarFallback",
    "Checkbox",
    "Switch",
    "Select",
    "Slider",
    "slider_classes",
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
    "Carousel",
    "ToastHost",
    "ToastItem",
    "DatePicker",
    "Chart",
]
