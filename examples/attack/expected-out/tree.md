# tree.md — illustrative attack run on `../sample-claim.md`

> ⚠️ **Illustrative, hand-authored example** (see
> [`confirmed.md`](confirmed.md) for the caveat). Abbreviated to the
> root + three CONFIRMED leaves to show the node format from
> `docs/ENGINE.md` §7.3; a real run carries all 12 fields per node and
> the REFUTED / MARGINAL branches too.

### root  Claim: caching layer makes the API 10× faster
- **central_claim**: "the new caching layer makes the API 10× faster"
  ([`../sample-claim.md:1`](../sample-claim.md))
- **method_skeleton**: in-memory LRU cache in front of the DB
  ([`../sample-claim.md:3`](../sample-claim.md))
- **key_evidence**: laptop benchmark p50 200 ms → 20 ms
  ([`../sample-claim.md:6`](../sample-claim.md))
- **explicit_assumptions**: TTL 60 s ⇒ fresh; 1-user test ⇒ ready
- **implicit_assumptions**: laptop ≈ production; p50 ≈ p99; concurrency
  1 ≈ concurrency N
- **children**: [C1, C2, C3]

### C1  "10× for all users in production" overgeneralizes a single-machine p50
- **parent**: root | **framing**: §3.F (scale extrapolation) | **score**: S=3 P=3 R=3 F=3 B=1 → total=13
- **verdict**: CONFIRMED
- **artifact_position**: [`../sample-claim.md:8`](../sample-claim.md)
- **proposed_fix**: scope the claim to "laptop p50"; load-test prod p99 before generalizing
- **children**: []

### C2  "never returns stale data" contradicted by the 60 s TTL
- **parent**: root | **framing**: §3.A (first-principles) | **score**: S=3 P=3 R=3 F=3 B=0 → total=12
- **verdict**: CONFIRMED
- **artifact_position**: [`../sample-claim.md:9-10`](../sample-claim.md)
- **proposed_fix**: "may serve data up to 60 s stale", or add write-through invalidation
- **children**: []

### C3  "production-ready" rests on a single-concurrent-user test
- **parent**: root | **framing**: §3.D (red team) | **score**: S=2 P=3 R=2 F=2 B=2 → total=11
- **verdict**: CONFIRMED
- **artifact_position**: [`../sample-claim.md:11-12`](../sample-claim.md)
- **proposed_fix**: gate "production-ready" on a concurrent load test + eviction-correctness check
- **children**: []
