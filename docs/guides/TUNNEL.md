# Tunnel DX — design, logic, and choices

**Audience:** maintainers and app authors who need to know *what* `uxdom serve --tunnel` does, *why* it exists, and *what it deliberately does not do*.

**Code:** `src/ux_dom/cli/tunnel.py` · wired from `cli/serve.py` · flags on `uxdom serve` / `dev` / `start`.

---

## 1. Problem we are solving

Developers expose a local ASGI app through an **edge** (ngrok, Cloudflare Tunnel, hosted sandboxes, reverse proxies). A common failure mode:

```text
Browser  ✓
Edge     ✓   (tunnel process is up)
Origin   ✗   (uvicorn not listening yet, or already dead)
→ HTTP 502 Bad Gateway
```

People then debug **caps, forms, Channel, Tailwind** — none of which caused the 502. The origin was simply not ready when the public URL was advertised, or the process exited while the tunnel stayed up.

**Goal:** never print or rely on a public URL until **local health is green**, and make the failure mode explicit when origin never comes up.

---

## 2. What we added (surface)

```bash
uxdom serve --tunnel ngrok
uxdom serve --tunnel cloudflare
uxdom dev --tunnel ngrok --port 8080
uxdom start --tunnel cloudflare   # rare; usually deploy to a real host instead

# Optional
--tunnel-token …          # or NGROK_AUTHTOKEN / TUNNEL_TOKEN env
--health-path /health     # default; falls back to /
--health-timeout 30       # seconds before fail
--host 0.0.0.0            # uvicorn bind (see §4)
```

| Flag | Default | Role |
|------|---------|------|
| `--tunnel` | `none` | `none` \| `ngrok` \| `cloudflare` (`cf` / `cloudflared` aliases) |
| `--tunnel-token` | env | Provider auth when required |
| `--health-path` | `/health` | First probe path; then `/` |
| `--health-timeout` | `30` | Fail closed with a clear error (mentions 502) |

When `--tunnel none` (default), behaviour is unchanged: in-process `uvicorn.run`, same as before.

---

## 3. Runtime sequence (why this order)

When `tunnel != none`:

```text
1. Tailwind (optional, same as normal serve)
2. Start uvicorn as a **subprocess** (so we can probe it from the parent)
3. wait_for_health(port, host=bind_host, path=/health → /)
4. Only then: start ngrok or cloudflared targeting the probe host:port
5. Print public URL; keep both processes alive; forward signals
```

If health never greens → **fail before** starting the tunnel. Message explicitly mentions 502 so authors map the symptom to the right layer.

---

## 4. `local_probe_host` (wildcard bind vs probe)

Uvicorn `--host 0.0.0.0` or `--host ::` binds all interfaces. Those strings are **not** valid client connection targets.

| Bind host | Probe host used for health + tunnel target |
|-----------|--------------------------------------------|
| `0.0.0.0`, `::`, `[::]`, `*` | `127.0.0.1` |
| concrete IP / hostname | used as-is |

This is the only place we rewrite the host. Concrete `--host 192.168.1.10` is respected so LAN / dual-stack setups keep working.

---

## 5. Non-goals (deliberate)

- Not a full reverse-proxy or production edge config
- Not Channel / caps / auth / CORS — those stay in app code
- Not changing default `serve` behaviour when `--tunnel` is omitted
- Not requiring ngrok/cloudflared at install time (optional PATH binaries)
- Not moving this into ux-app or ux-channel

---

## 6. Author checklist

1. `uxdom serve --tunnel ngrok` (or cloudflare)
2. Wait for local health log line
3. Use the printed public URL
4. If you see 502: origin died or never started — check the process, not the tunnel
