# Deploy

**Product deploy** is on **ux-compose**:

```bash
uxcompose deploy --provider docker   # fly | render | railway | vps | checklist
```

ASGI entry for compose apps: `uvicorn app:asgi`.

XElement is served from the installed package at `/ux-dom/static/x_element.js`
(no app copy into `assets/js/`).

ux-dom does not own product deploy configs. Product CSS: `uxcompose build`.
Pure-dom Document/static verify for leftover `app/main.py` trees: `uxdom build`.
