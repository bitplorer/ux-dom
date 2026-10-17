# Counter: ux-dom × ux-channel

ux-dom builds the document and the markup; ux-channel signs the controls,
runs the actions and sends back the re-rendered region. Checked against
ux-channel `f1a93fc`.

```bash
pip install "ux-channel @ git+https://github.com/bitplorer/ux-channel.git@f1a93fcf298c97a59fa6538697731e19aac8586d#subdirectory=python"
# from the repository root
uvicorn examples.ux_channel_counter.main:app --reload
```

| File | Owner | What it does |
|------|-------|--------------|
| `channel.py` | ux-channel | `Channel.boot`, the `counter` region (`@ch.region`), the `add` / `reset` actions (`@ch.on(refresh=[counter])`) |
| `components.py` | ux-dom | `CounterCard`, `Region` (puts `ch.html(region)` into the tree as trusted `Markup`) |
| `main.py` | both | `Document(...).use(Channel(), Csp.auto())`, buttons with `ch.control(...).as_dict()`, route table |

The flow:

1. `GET /` renders `Region(html=ch.html(counter))`: the region wrapped in
   `data-channel-id="counter"`.
2. Each button gets `ControlAttrs`: `data-channel-action`, `data-channel-args`
   (the trusted arguments, e.g. `{"step": 5}`) and a signed `data-channel-cap`.
   `button(label, **ch.control(add, trust_step=5).as_dict())`; ux-dom escapes
   the values.
3. `ux-channel.js` posts `{"v": "1", "action", "args", "cap"}` to
   `/ux-channel/action`. A changed argument fails the signature (401).
4. The action updates `ch.draft`; the reply carries a `morph` op with the
   refreshed region, which the client swaps in.

`ux_dom.runtime.Channel` only adds the client `<script>` tags (nonce-stamped
by the CSP runtime); `Channel.boot` serves the files. The development memory
store keeps one counter per process, shared by all visitors.

Tests: `tests/08_examples/test_ux_channel_counter.py`.
