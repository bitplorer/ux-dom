# UxDom production examples

> Prefer **`uxcompose create-app myapp`** for greenfield product apps.
> These folders are **ux-dom-only render demos**, not the product routing path.
> See [DX.md](../docs/guides/DX.md).

Runnable, production-shaped apps demonstrating **ux_dom alone**. ux-compose and
ux-channel own the integration examples ([ADR 0003](../docs/adr/0003-layer-boundary.md)).

## Layout

| App | Path | Stack | Port |
|-----|------|-------|------|
| Realtime kit | [`ux_dom_only/realtime_kit`](ux_dom_only/realtime_kit/) | SSE, streaming HTML | 8092 |
| XElement kit | [`xelement_kit`](xelement_kit/) | Light/Shadow DOM, HTMX, Alpine, slots | 8080 |
| UI kit gallery | [`ux_kit`](ux_kit/) | `ux_dom.ui` components | 8080 |

## Capability matrix

| Capability | realtime_kit |
|------------|:---:|
| Components / Document | ✓ |
| SSE | ✓ |
| StreamingResponse | ✓ |

## Run

```bash
# from repo root
export PYTHONPATH=.
uvicorn examples.ux_dom_only.realtime_kit.app:app --host 0.0.0.0 --port 8092
```

## Tests

```bash
python -m pytest tests/04_production/test_examples_production.py -q
```

### XElement kit (HTMX / Alpine / Web Components)

See [`xelement_kit/`](xelement_kit/).

- Light/Shadow full guides: [`xelement_kit`](xelement_kit/) ·
  [`docs/reference/XELEMENT.md`](../docs/reference/XELEMENT.md) ·
  [`docs/reference/HYPERMEDIA.md`](../docs/reference/HYPERMEDIA.md)

### ux_kit

Shadcn-inspired `ux_dom.ui` gallery (+ optional channel bridge). See
[docs/reference/UI.md](../docs/reference/UI.md).
