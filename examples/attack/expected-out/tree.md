# tree.md — abridged capped attack run on `../sample-claim.md`

> ⚠️ **Abridged output of a real capped run**
> (`--width 3 --depth 1 --no-online --no-grill`), **hand-trimmed** to
> the root + CONFIRMED leaves to document the node format from
> `docs/ENGINE.md` §7.3. The trimming, not the cap, is why the rest is
> absent: any real run carries the REFUTED / MARGINAL branches and a
> full 12-field derivation per node, capped or not (`docs/ENGINE.md`
> §F7).

### root  Claim: caching layer makes the API 10× faster
- **central_claim**: "our new caching layer makes the API 10× faster"
  ([`../sample-claim.md:1`](../sample-claim.md))
- **method_skeleton**: "an in-memory LRU cache in front of the database"
  ([`../sample-claim.md:3`](../sample-claim.md))
- **key_evidence**: "p50 latency dropped from 200 ms to 20 ms" on a
  developer-laptop benchmark ([`../sample-claim.md:4-5`](../sample-claim.md))
- **explicit_assumptions**: 10× generalizes to "all users in production"
  (:6); 60 s TTL ⇒ "never returns stale data" (:7-8); one-user no-errors
  ⇒ "production-ready" (:9-10)
- **implicit_assumptions**: laptop perf ≈ production (:4); p50 ≈ p99 tail
  (:4-5); concurrency 1 ≈ concurrency N (:9); benchmark hit-rate ≈ prod
  hit-rate; LRU eviction correct under concurrent access
- **children**: [C1, C2, C3]

### C1  "10× for all users in production" overgeneralizes a single-machine p50
- **parent**: root | **framing**: §3.F (scale extrapolation) | **score**: S=3 P=3 R=3 F=3 B=1 → total=13
- **verdict**: CONFIRMED
- **artifact_position**: [`../sample-claim.md:6`](../sample-claim.md) — "Therefore the API is 10× faster for all users in production."
- **artifact_defense**: none found (read all of lines 1-10; no production load-test or p99 result cited)
- **proposed_fix**: scope the claim to "p50 on a dev laptop"; load-test production p99 before generalizing to all users
- **children**: []

### C2  "never returns stale data" contradicted by the 60 s TTL
- **parent**: root | **framing**: §3.A (first-principles) | **score**: S=3 P=3 R=3 F=3 B=0 → total=12
- **verdict**: CONFIRMED
- **artifact_position**: [`../sample-claim.md:7-8`](../sample-claim.md) — "never returns stale data, because entries expire after 60 seconds."
- **artifact_defense**: none (read all of lines 1-10; no write-through / invalidation-on-write mechanism described)
- **proposed_fix**: replace with "may serve data up to 60 s stale", or add write-through invalidation
- **children**: []

### C3  "production-ready" rests on a single-concurrent-user test
- **parent**: root | **framing**: §3.D (red team) | **score**: S=2 P=3 R=2 F=2 B=2 → total=11
- **verdict**: CONFIRMED
- **artifact_position**: [`../sample-claim.md:9-10`](../sample-claim.md) — "tested with one concurrent user and saw no errors, so the cache is production-ready."
- **artifact_defense**: none (read all of lines 1-10; no concurrent load or eviction-correctness test described)
- **proposed_fix**: gate "production-ready" on a concurrent load test + eviction-correctness check; until then say "passed a smoke test"
- **children**: []
