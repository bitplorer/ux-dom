# UxDom TLA+ verification

Formal models of concurrent / protocol **intents**, model-checked with **TLC**.

| Spec | Intent | Status |
|------|--------|--------|
| `ContextStack` | Per-worker `with` stack; build ≠ render; single owner | TLC ✓ |
| `UniqueId` | Locked generator uniqueness (forward clock, seed envelope) | TLC ✓ |
| `UniqueIdSafe` | Hardened: refuse re-issue on seed wrap | TLC ✓ |
| `WebSocketIsolation` | `share_instance=FALSE` per-connection state | TLC ✓ |
| `RouteVsDom` | Route classmethods co-exist with instance DOM API | TLC ✓ |
| `RenderIdempotent` | Sticky controls; frozen tree multi-render equal | TLC ✓ |

## Run

```bash
./run_tlc.sh                 # all specs
./run_tlc.sh ContextStack    # one
```

Requires **Java 11+** and `tla2tools.jar` in this directory.

## Python mapping

| Spec | Implementation |
|------|----------------|
| ContextStack | `ux_dom/dom/src/dom_tag.py` (`_context_key`, enter/exit) |
| UniqueId | `ux_dom/dom/uniqueid.py` (`_uid_lock`, seed bump) |
| WebSocketIsolation | `ux_dom/web_io/_adapter.py` (`_instances`) |
| RouteVsDom | `ux_dom/dom/src/component.py` (`_DOM_INSTANCE_API`) |
| RenderIdempotent | sticky `_control` / `open_tag` on render |

## Discovery notes

Unbounded seed wrap + clock skew can collide in the abstract uniqueid algorithm.
Production uses a 14-bit seed + lock; `UniqueIdSafe` models a harden option
(reject already-issued ids).
