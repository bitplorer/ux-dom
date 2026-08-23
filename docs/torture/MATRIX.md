# UX-Stack Torture Matrix — Phase 1

> Branch protocol: work only on `torture/matrix-phase1` (or successor).
> **Never** force-push `main`. **Never** rewrite history. Additive tests only.

## NORTH_STAR

Reversible, ownership-law-respecting torture matrix that proves security + stability
under adversarial, concurrent, residual-ownership, and protocol stress — with zero
loss of git history and zero unforced writes to main.

## Categories (finite)

| ID | Name | Phase 1 bar |
|----|------|-------------|
| OWN | Ownership residual / hard-cut | S0 — must fail gate if broken |
| ADV | Adversarial input (XSS, path, injection) | S0/S1 |
| RACE | Concurrency / double-invoke / races | S1 |
| AUTH | Cap / intent / authz boundary | S1 where channel applies |
| PROT | Protocol / fuzz edges | S2 default (channel depth Phase 2) |
| HARD | Production hardening edges | S1 |
| REG | Regression locks for FLOW law | S0 |

Severity: **S0** gate-fail · **S1** must fix before SHIP · **S2** documented residual · **S3** Phase 2/3

## Library coverage (Phase 1)

| Library | OWN | ADV | RACE | AUTH | HARD | REG |
|---------|-----|-----|------|------|------|-----|
| ux-dom | required | required | map existing | n/a | map existing | required |
| ux-compose | required | required | map existing | soft | map existing | required |
| ux-channel | map existing | map existing | map existing | required | map existing | soft |
| ux-behavior | required | required | soft | soft | soft | soft |
| ux-motion | required | soft | soft | n/a | soft | soft |
| ux-app | required | soft | soft | soft | soft | soft |

## Repo safety (invariant)

1. Feature branch only for new torture commits.
2. Single-agent GitHub connector when concurrent writers exist.
3. No force-push to `main`.
4. No deletion of green tests without replacement evidence.
5. Soak / multi-hour chaos **excluded** from Phase 1 default gate.

## Phase 1 command subset (agents run; do not require user)

```bash
# ux-dom
python -m unittest tests.07_torture tests.05_chaos.test_pentest_chaos -q
# ux-compose
pytest tests/regression tests/security -q
```

## Soak (Phase 2 — not Phase 1 gate)

Long chaos, browser farms, multi-hour stress, full channel fuzz corpus expansion.
