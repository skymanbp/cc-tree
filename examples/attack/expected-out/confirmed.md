# confirmed.md — abridged capped attack run on `../sample-claim.md`

> ⚠️ **Abridged output of a real capped run**
> (`--width 3 --depth 1 --no-online --no-grill`) on the toy artifact
> [`../sample-claim.md`](../sample-claim.md), **hand-trimmed** to the
> root + CONFIRMED leaves to document the deliverable format. The
> trimming, not the cap, is why the rest is absent: any real run —
> capped or not — also writes `tree.json`, `marginal.md`, `refuted.md`,
> a `REPORT.md`, and a full 12-field derivation per node, because
> `docs/ENGINE.md` §F7 requires every visible leaf to be complete even
> when a cap trips. Sorted by severity (S) descending.

## C1 — "10× faster for all users in production" overgeneralizes a single-machine p50 (S=3)

- **artifact_position**: [`../sample-claim.md:6`](../sample-claim.md) —
  "Therefore the API is 10× faster for all users in production."
- **evidence**: The 10× number comes from lines 4-5 — a *p50* measurement
  on *one developer laptop*. Production p50 ≠ laptop p50 (different CPU,
  cache size, working set), and p50 says nothing about the p99 tail that
  real users actually feel. The conclusion's quantifiers ("all users",
  "10×") are strictly stronger than the evidence (one machine, one
  percentile).
- **artifact_defense**: none found — read all of lines 1-10; no
  production measurement, p99 figure, or load-test result appears.
- **proposed_fix**: restate as "p50 dropped ~10× on a dev laptop;
  production p99 under real load not yet measured", or add a production
  load-test result before keeping the "all users / 10×" claim.

## C2 — "never returns stale data" is contradicted by the 60 s TTL in the same sentence (S=3)

- **artifact_position**: [`../sample-claim.md:7-8`](../sample-claim.md) —
  "never returns stale data, because entries expire after 60 seconds."
- **evidence**: A 60 s TTL *is* a staleness window — a row updated in the
  DB at t=0 is served from cache as stale until its entry expires (up to
  60 s later). "Never stale" and "expires after 60 s" are mutually
  exclusive: the justifying clause refutes the claim it justifies. The
  contradiction is reproducible from the single sentence.
- **artifact_defense**: none — read all of lines 1-10; no write-through
  or invalidation-on-write mechanism is described that would close the
  window.
- **proposed_fix**: replace "never returns stale data" with "may serve
  data up to 60 s stale", or add write-through invalidation if true
  freshness is required.

## C3 — "production-ready" rests on a single-concurrent-user test (S=2)

- **artifact_position**: [`../sample-claim.md:9-10`](../sample-claim.md) —
  "tested with one concurrent user and saw no errors, so the cache is
  production-ready."
- **evidence**: One concurrent user exercises none of the failure modes a
  shared in-memory LRU cache has under production concurrency: eviction
  races, thundering-herd on a cold key, lock contention, per-instance
  cache divergence behind a load balancer. "No errors at concurrency 1"
  does not support "production-ready".
- **artifact_defense**: none — read all of lines 1-10; no concurrent load
  test, eviction-correctness check, or multi-instance consideration
  appears.
- **proposed_fix**: gate the "production-ready" claim on a concurrent load
  test (≥ realistic peak QPS) and an eviction/invalidation correctness
  check; until then downgrade to "passed a single-user smoke test".
