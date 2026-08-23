# Tunnel / public share

Product serve lives on **uxcompose**. Expose with host tooling:

```bash
uxcompose serve app:asgi --port 8080
# then: ngrok http 8080   or   cloudflared tunnel --url http://127.0.0.1:8080
```

ux-dom does not ship a product tunnel CLI.
