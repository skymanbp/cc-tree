# Example — `attack` preset

A minimal, **illustrative** example of the `attack` preset on a toy
artifact.

- [`sample-claim.md`](sample-claim.md) — the artifact under attack: a
  5-point argument with three planted flaws (an overgeneralized
  benchmark, a self-contradicting freshness claim, and a
  concurrency-blind "production-ready" conclusion).
- [`expected-out/confirmed.md`](expected-out/confirmed.md) — the
  primary deliverable: the three CONFIRMED critiques, each with
  `file:line` position, evidence, and a concrete `proposed_fix`.
- [`expected-out/tree.md`](expected-out/tree.md) — the same critiques in
  the `docs/ENGINE.md` §7.3 node format (root + 3 leaves).

> ⚠️ The files under `expected-out/` are **hand-authored to document the
> output format**, not the product of a real engine run. A real run
> (`/cc-tree:attack ./sample-claim.md`) additionally produces
> `tree.json`, `marginal.md`, `refuted.md`, a `REPORT.md`, and a full
> 12-field derivation per node, and may surface more critiques than the
> three shown here.

## Regenerate it for real

```bash
/cc-tree:attack ./examples/attack/sample-claim.md --out ./examples/attack/real-out/
```

Then compare `real-out/confirmed.md` against `expected-out/confirmed.md`:
the three planted flaws above should all appear as CONFIRMED, with
`file:line` positions pointing into `sample-claim.md`.
