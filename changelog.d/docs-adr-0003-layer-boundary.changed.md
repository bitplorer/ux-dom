- **Docs: ADR 0003 records the ux-dom / ux-compose layer boundary.** It lists what stays in
  ux-dom, what moves, the three capabilities ux-compose still lacks, and the rule that
  residue is removed only after ux-compose ships the equivalent or the owner records a
  waiver. Serve examples now use ``uxcompose serve dev app:asgi`` (a mode is required),
  the nonexistent ``--hmr`` flag is gone, and ``docs/guides/TUNNEL.md`` is a moved stub.
