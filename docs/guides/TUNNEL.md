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
5. Print banner including public URL
6. Wait; if origin or tunnel exits → non-zero exit + cleanup
```

**Why subprocess origin?**  
In-process `uvicorn.run` blocks; we cannot health-check “ourselves” from the same thread before binding. Subprocess keeps the parent free to probe and own tunnel lifecycle.

**Why health before tunnel?**  
Starting the tunnel first is exactly how you get a public URL that 502s. Edge up + origin down is the bug class this DX exists to prevent.

**Why fail closed on health timeout?**  
Silent “tunnel ready” with a dead origin is worse than a loud local error. Message explicitly points at origin-down / 502 so authors do not chase Channel or form bugs.

---

## 4. Bind host vs probe host (`local_probe_host`)

Uvicorn `--host` is a **bind** address. Health checks and tunnel clients need a **connect** address.

| Bind (`--host`) | Probe / tunnel target | Reason |
|-----------------|----------------------|--------|
| `0.0.0.0`, `::`, `*` | `127.0.0.1` | Wildcard is not a valid client destination |
| `127.0.0.1` | `127.0.0.1` | As bound |
| `192.168.1.20` | `192.168.1.20` | Reach the chosen interface |
| hostname | hostname | As bound |

**Choice:** do not hardcode `127.0.0.1` for the app origin. Map wildcards to loopback; pass concrete binds through.  
**Exception:** ngrok’s **local API** remains `http://127.0.0.1:4040` — that is ngrok’s control plane on the machine, not the app bind.

---

## 5. Provider choices (and non-choices)

| Provider | Binary | How we get the public URL |
|----------|--------|---------------------------|
| **ngrok** | `ngrok` on PATH | Poll `http://127.0.0.1:4040/api/tunnels` after `ngrok http <target>` |
| **cloudflare** | `cloudflared` on PATH | Parse `https://*.trycloudflare.com` from process output (quick tunnel) |

**Why only these two (for now)?** Widely used for share-local-dev; no new Python deps.

**Out of scope:** production deploy (`uxdom deploy`), named Cloudflare tunnels, remote ephemeral VM survival, putting this in ux-app or ux-channel.

---

## 6. Ownership in the stack

```text
ux-dom CLI   →  serve / build / deploy / tunnel   (process + assets)
ux-app       →  create-app / add ui layers on uxdom; app isolation doctor
ux-channel   →  Intent → Result, caps, wire doctor/explain
```

---

## 7. Design principles (keep if you extend)

1. **Public URL only after local health** — never invert that order.
2. **Bind ≠ probe** — wildcards map to loopback; concrete binds pass through.
3. **Optional binaries** — no hard dependency on ngrok/cloudflared for default serve.
4. **Loud origin failure** — timeout text must mention 502 / origin-down.
5. **Deploy stays deploy** — tunnels are for share-local-dev.
6. **Default path frozen** — `uxdom serve` without `--tunnel` keeps in-process uvicorn.

---

## Related

- [CLI.md](CLI.md) · [DX.md](DX.md) · [FEATURES.md](../FEATURES.md)
- Code: `src/ux_dom/cli/tunnel.py`, `src/ux_dom/cli/serve.py`
