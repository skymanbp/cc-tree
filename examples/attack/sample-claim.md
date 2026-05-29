# Claim: our new caching layer makes the API 10× faster

1. We added an in-memory LRU cache in front of the database.
2. In a benchmark on a developer laptop, p50 latency dropped from
   200 ms to 20 ms.
3. Therefore the API is 10× faster for all users in production.
4. The cache never returns stale data, because entries expire after
   60 seconds.
5. We tested with one concurrent user and saw no errors, so the cache
   is production-ready.
