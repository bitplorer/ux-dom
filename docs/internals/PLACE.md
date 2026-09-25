# Place in the stack

**You are here:** `ux-dom` in [bitplorer/ux-dom](https://github.com/bitplorer/ux-dom).

The render layer. Server-authored HTML: Document, elements, serialize, page discovery. A tree stays a tree until something official serializes it.

The picture is the same in every repo. The thick stroke is this library. A missing line is a missing door, not a forgotten one. Dashed lines are history.

## Owns

HTML, CSS, and JS trees, the Document shell, pure discovery, and package static.

## Refuses

Intent, Caps, Result ops, Morph state, motion IR, and the product CLI.

## Install

pip install ux-dom. Import ux_dom. CLI uxdom. Python 3.14 or newer.

## Doors

### Used by

- [ux-compose](https://github.com/bitplorer/ux-compose) — imports Document
- [ux-motion](https://github.com/bitplorer/ux-motion) — html stays a tree
- [ux-surface](https://github.com/bitplorer/ux-surface) — was shells (history)

## The stack

```mermaid
flowchart TB
  appic["appic"]
  compose["ux-compose"]
  dom["ux-dom"]
  behavior["ux-behavior"]
  motion["ux-motion"]
  channel["ux-channel"]
  host["cek-host"]
  surface["cek-surface"]
  hw["cek-hw"]
  runtime["cek-runtime"]
  law["cek-framework"]
  retired["ux-surface · retired"]
  classDef here stroke-width:3px
  class dom here
  appic -->|authored in| compose
  compose -->|imports Document| dom
  compose -->|imports behavior| behavior
  compose -->|imports scenes| motion
  compose -->|wire door only| channel
  behavior -->|live Caps, optional| channel
  motion -->|html stays a tree| dom
  channel -->|Cap machine| host
  surface -->|depends on Host| host
  host -->|same declared pairs| runtime
  surface -->|carriers, not a second kernel| runtime
  runtime -->|implements the law| law
  host -->|binds the law| law
  hw -->|plugs project_ops| host
  hw -->|hw world, same axioms| law
  retired -.->|was shells| dom
  retired -.->|was commands| channel
```

## The walk

Mint, intent, verify, project, apply, undo.

1. **Mint.** Host mints a Cap. The subject on the Cap is the subject in the args. dev is the workshop. prod refuses the workshop secret.
2. **Intent.** Channel carries action, args, and cap. That is the click. It is not a form post.
3. **Verify.** Host verifies the Cap before any shared-world write. A bad Cap, or a store that is down, refuses. ops is empty. The peer never mints.
4. **Project.** Only declared pairs leave the host. Baseline and ui.dom are the catalog. Hardware pairs arrive through project_ops. They are not a fork of Host.
5. **Apply.** The peer applies the ops. DOM is one world. GPIO is another. Surface carries the IR. It does not decide.
6. **Undo.** Lineage records the cause. End or revoke reverses it, or the op is marked non-reversible. A trace id never grants permission.

ux-dom is the world a peer may paint. It does not decide, and it does not carry the Intent.

## Notes

- Product commands live on uxcompose, not uxdom.
- Element style="" is style-src-attr, not style-src.
- The dom-and-channel glue reference stays at docs/reference/STACK.md. This page is the wider stack.
