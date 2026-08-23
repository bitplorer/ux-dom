# Deploy

**Product deploy** is on **ux-compose**:

```bash
uxcompose deploy --provider docker   # fly | render | railway | vps | checklist
```

ASGI entry for compose apps: `uvicorn app:asgi`.

ux-dom does not own product deploy configs. Pure-dom asset verify: `uxdom build`.
