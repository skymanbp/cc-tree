# confirmed.md — illustrative attack run on `../sample-claim.md`

> ⚠️ **Illustrative, hand-authored example.** This file shows the
> *shape* of an `attack` preset deliverable on the toy artifact
> [`../sample-claim.md`](../sample-claim.md). It was written by hand to
> document the output format — it is **not** the product of a real
> engine run (a real run also produces `tree.json`, `marginal.md`,
> `refuted.md`, and a full 12-field derivation per node). Sorted by
> severity (S) descending.

## C1 — "10× faster for all users in production" overgeneralizes a single-machine p50 (S=3)

- **artifact_position**: [`../sample-claim.md:8`](../sample-claim.md) —
  "Therefore the API is 10× faster for all users in production."
- **evidence**: The 10× number comes from line 6-7: a *p50* measurement
  on *one developer laptop*. Production p50≠laptop p50 (different CPU,
  cache size, working set), and p50 says nothing about p99 — the tail
  users actually feel. No production load test is cited anywhere in the
  artifact. The conclusion quantifier ("all users", "10×") is strictly
  stronger than the evidence (one machine, one percentile).
- **artifact_defense**: none found in lines 1-9.
- **proposed_fix**: restate as "p50 dropped 10× on a dev laptop; we have
  not yet measured production p99 under real load", or add a production
  load-test result before keeping the "all users / 10×" claim.

## C2 — "never returns stale data" is contradicted by the 60 s TTL in the same sentence (S=3)

- **artifact_position**: [`../sample-claim.md:9-10`](../sample-claim.md)
  — "never returns stale data, because entries expire after 60 seconds."
- **evidence**: A 60 s TTL *is* a staleness window: a row updated in the
  DB at t=0 is served from cache as stale until the entry expires (up to
  60 s later). "Never stale" and "expires after 60 s" are mutually
  exclusive; the justifying clause refutes the claim it justifies.
- **artifact_defense**: none (no write-through / invalidation-on-write
  mechanism is described).
- **proposed_fix**: replace "never returns stale data" with "may serve
  data up to 60 s stale", or add write-through invalidation if true
  freshness is required.

## C3 — "production-ready" rests on a single-concurrent-user test (S=2)

- **artifact_position**: [`../sample-claim.md:11-12`](../sample-claim.md)
  — "tested with one concurrent user and saw no errors, so the cache is
  production-ready."
- **evidence**: One concurrent user exercises none of the failure modes
  a shared in-memory LRU cache has under production concurrency: eviction
  races, thundering-herd on a cold key, lock contention, per-instance
  cache divergence behind a load balancer. "No errors at concurrency 1"
  does not support "production-ready".
- **artifact_defense**: none.
- **proposed_fix**: gate the "production-ready" claim on a concurrent
  load test (≥ realistic peak QPS) and an eviction/invalidation
  correctness check; until then downgrade to "passed a smoke test".
