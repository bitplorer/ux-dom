# Copyright (c) 2023 UxDom
#
# This software is released under the MIT License.
# https://opensource.org/licenses/MIT

from pathlib import Path
from types import SimpleNamespace

from starlette.config import Config
from starlette.websockets import WebSocket

BASE_DIR = Path(__file__).parent

# load .env file contents
config = Config(BASE_DIR / ".env")

# set debug variable
DEBUG = config("DEBUG", cast=bool, default=False)

# Demo-local folders — not ux_dom.WebAssets (that class moved to ux-compose).
ASSETS_DIR = BASE_DIR / "assets"
webassets = SimpleNamespace(
    dir=ASSETS_DIR,
    static=SimpleNamespace(
        css=ASSETS_DIR / "static" / "file" / "css",
        js=ASSETS_DIR / "static" / "file" / "js",
        image=ASSETS_DIR / "static" / "media" / "image",
    ),
    template=SimpleNamespace(dir=ASSETS_DIR / "templates"),
)

if DEBUG:
    from ux_dom import reloader

    # hot reloading via websocket instance

    async def tailwind_watcher():
        from demosite.tailwindcss import tailwind

        await tailwind.async_run()

    hot_reload_route = reloader.HotReloadWebSocketRoute(
        websocket_type=WebSocket,
        watch_paths=[
            reloader.WatchPath("./demosite", on_reload=[tailwind_watcher]),
            reloader.WatchPath("./ux_dom"),
        ],
        url_path="/hot-reload",
        url_name="hot_reload",
        reconnect_interval=1,
    )
