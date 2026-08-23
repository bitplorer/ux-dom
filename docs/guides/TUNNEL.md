# Tunnel / public share

> **Diátaxis:** how-to · **Canonical:** `docs/guides/TUNNEL.md` · **Layer:** ux-dom  
> Map: [INDEX.md](../INDEX.md).

Product serve lives on **uxcompose**. Expose with host tooling:

```bash
uxcompose serve app:asgi --port 8080
# then: ngrok http 8080   or   cloudflared tunnel --url http://127.0.0.1:8080
```

ux-dom does not ship a product tunnel CLI.
