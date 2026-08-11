# Why JS needs a URL (and Python does not)

## The confusion

| Python | JavaScript in the browser |
|--------|---------------------------|
| `import ux_dom` loads bytes from site-packages | Browser **cannot** import from site-packages |
| Interpreter finds files on disk | Browser only loads via **HTTP URL** (`<script src="…">`) |
| One copy on disk is enough | That same file must be **exposed at a URL** |

So the library *is* already packaged with the app after `pip install`.
The only extra job is: **map package path → public URL**.

```text
  site-packages/ux_dom/scripts/x_element.js     ← only copy (pip owns it)
           │
           │  App.build mounts StaticFiles
           ▼
  GET /ux-dom/static/x_element.js           ← URL the browser can load
           │
           │  <script src="…"> from shell_fragments()
           ▼
  Document head
```

There is **no second copy** under `assets/`.  
Copying into `assets/` would mean:

- two files to keep in sync  
- upgrades (`pip install -U ux_dom`) leave a **stale** `assets/js/x_element.js`  
- `uxdom build` becomes a duplicate ship step for no gain  

## What *does* go in `assets/`?

Things **you** author for this app (not pip packages):

- Tailwind CSS input/output  
- images, fonts  
- app-specific JS you wrote in the project  

## uxchannel does the same

```text
site-packages/ux_channel/static/ux-channel.js
        → GET /ux-channel/static/ux-channel.js
        → ch.scripts() / UxChannelRuntime tags
```

## Day-1 usage (you don’t think about mounts)

```python
App().use(XElementRuntime())   # injects script URL + mounts package dir
```

`shell_fragments(get_hub())` puts the tag in the document.  
`App.build()` wires the StaticFiles mount. Browser gets one consistent file.

## Security note

Exposing a **URL** must not mean exposing the **filesystem**.

ux-dom registers **one route per allowlisted file** (e.g. only `x_element.js`).
It does **not** mount the package directory. Requests for `__init__.py` or
`../` paths return 404/403. See `ux_dom.plugins.safe_static` and `docs/security/ASSETS.md`.
