# The 12 framings

> 🌐 中文平行版：[`framings.zh.md`](framings.zh.md)（this English file is canonical).

This document expands §3.A–§3.L from [`ENGINE.md`](ENGINE.md) into
operational prompts with **per-preset examples**. The engine runs
all 12 framings on every node, every round, with each framing
producing ≥ 1 child branch. Skipping or weakening a framing voids
the round.

Each framing below has the same structure:
1. **One-line purpose** (universal).
2. **Operational prompt** (universal — what the engine asks itself
   at each node).
3. **Per-preset flavor** (`brainstorm` / `attack` / `design` /
   `code-audit`) — concrete examples of what a child branch looks
   like in each context.
4. **Output requirement** (always ≥ 1 child branch with §4 field-1
   draft-filled; full §4 derivation happens after pass completion).

---

## §3.A — First-principles

**Purpose.** Strip the node's load-bearing assumptions one at a time
and ask what's still true after each removal.

**Prompt.** List every assumption the current node depends on (load
the §4 `assumptions` field if present). For each, mentally remove it
and ask: *"with this assumption gone, what remains structurally
sound?"* Emit a child branch whose subject is the residual claim.

**Per-preset flavor:**

- **brainstorm.** "If we drop the assumption that the dark-matter
  halo is spherical, the secondary-peak signal becomes a function of
  triaxial orientation — there's a new SNR_resolved derivation
  contingent on observer angle that's worth exploring."
- **attack.** "The paper's central claim assumes lensing
  cross-correlation noise is Gaussian (§3, line 412). If that
  assumption is dropped, the χ² goodness-of-fit reduces to a
  permutation test, and the reported 4.2σ becomes 2.1σ."
- **design.** "The auth flow assumes single-tenancy. Drop that and
  the JWT scheme requires tenant-scoped key rotation — adds two
  config knobs but lets the same code serve B2B."
- **code-audit.** "[upload.py:42](#L42) assumes the uploaded file's
  declared MIME-type matches its content. Strip that assumption →
  add a magic-byte sniff before storage to prevent
  content-type-spoofing → polyglot uploads."

**Output.** ≥ 1 child branch whose subject is the *minimum-claim
after assumption removal*, with the removed assumption explicitly
named in field-5 `assumptions`.

---

## §3.B — Inversion (negation / dual / boundary-of-failure)

**Purpose.** The node is exploring / asserting / proposing X.
Explore ¬X, the dual of X, or the boundary at which X fails.

**Prompt.** What's the opposite of the current node's direction?
What's its dual (in the math / category / system sense)? Where does
this approach mechanically break down? Emit a child branch
exploring one of these inverses.

**Per-preset flavor:**

- **brainstorm.** "We've been looking at how *lensing* tells us
  about dark matter. The dual: how does dark-matter substructure
  *change* the lensing PSF in ways photometric residuals could
  detect without explicit lensing measurement?"
- **attack.** "The paper claims method M outperforms baseline B. The
  inversion: where does B outperform M? §5 only shows results in the
  high-SNR regime — what about z > 0.8 where M's training data is
  sparse?"
- **design.** "Current proposal: build our own auth service. The
  inversion: outsource auth entirely (e.g. Auth0 / Clerk) and own
  only the user-mapping layer. Costs trade differently."
- **code-audit.** "[parser.py:88](#L88) handles malformed UTF-8 by
  silently dropping bytes. The inversion: raise loudly. Trade-off:
  blocks one rare upload-stuck bug, but breaks any historic data
  with mixed encodings."

**Output.** ≥ 1 child branch exploring the inverse, with the
inversion explicitly stated and a `falsifiability` / `artifact_defense`
that explicitly compares to the original direction.

---

## §3.C — Cross-disciplinary

**Purpose.** Borrow tooling, framing, or evidence standards from
fields outside the node's home discipline.

**Prompt.** List ≥ 3 external fields where a *structurally
isomorphic* problem appears. For each, ask: *"what's the standard
tool in that field, and would transplanting it here work?"* Emit a
child branch around the most-promising transplant.

**Per-preset flavor:**

- **brainstorm.** "WGL substructure detection is structurally
  similar to (1) genomic CNV detection (statistical detection of
  bumps on a noisy 1D signal), (2) gravitational-wave event
  detection (matched-filter against a template bank), (3) anomaly
  detection in industrial sensor streams. The matched-filter
  approach from GW could potentially be transplanted with adapted
  templates from N-body sims."
- **attack.** "An ML reviewer would attack §4's evaluation
  methodology for *data leakage*: the train/test split is by halo
  ID but cross-realization correlations weren't accounted for. An
  econometrics reviewer would attack the same section for *endogeneity*
  — the simulation choices condition both M and the test metric."
- **design.** "Auth-service design parallels rate-limiting design.
  The standard rate-limiter pattern (token bucket + Redis cluster)
  suggests a similar pattern for auth-tokens (short-lived bucket +
  refresh ring), which we hadn't considered."
- **code-audit.** "A database-engineer reviewer would attack
  [migrations/0042.sql:15](#L15) for missing `CONCURRENTLY` on the
  index creation — long-locking migration on a hot table. A
  distributed-systems reviewer would attack the same line for not
  being idempotent — restart-mid-migration leaves partial state."

**Output.** ≥ 1 child branch transplanting the external-field
approach, with `assumptions` listing what invariants might break in
the transplant.

---

## §3.D — Adversarial / red team

**Purpose.** Adopt the stance of a reviewer (or attacker) actively
trying to refute / break / sabotage the current node, and emit the
strongest counter-arguments.

**Prompt.** "What are the **3 most damaging** counter-arguments to
this node? Each must be specific (point to a file:line / a
mechanism / a concrete failure) — no vague 'might not generalize'."
Emit a child for the strongest counter, reformulated as a
refutation experiment (brainstorm/design) or a
confirmed-or-refuted critique (attack/code-audit).

**Per-preset flavor:**

- **brainstorm.** "Strongest counter to 'detect substructure via
  shape-bias residuals': the residual signal might be entirely
  explained by intrinsic-alignment contamination, not substructure.
  Test design: simulate two universes with identical halo content
  but different IA strength; if the proposed method confounds them,
  the direction is dead."
- **attack.** "Strongest counter to the paper's central claim:
  Fig. 5 shows the method works at z < 0.5, but the test set's z >
  0.8 results are missing from the body and only appear in the
  supplementary. This is a selective-reporting pattern."
- **design.** "Strongest counter to 'build our own auth':
  maintenance cost of password-reset + 2FA + SAML support is roughly
  0.5 engineer-year/year, and the team is already short-staffed.
  Refutation: estimate actual engineering hours for the next 4
  quarters of auth maintenance."
- **code-audit.** "Strongest counter to '[upload.py:42](#L42) is
  safe': the magic-byte sniff only checks the first 4 bytes. A ZIP
  bomb has standard magic bytes. Refutation: try it — should be a
  CVE in 10 minutes."

**Output.** ≥ 1 child branch carrying the strongest counter, with
the counter-argument formulated as a falsifiable test or a concrete
critique with `proposed_fix`.

---

## §3.E — Constraint variation (relax / tighten)

**Purpose.** List the node's explicit and implicit constraints, then
explore both relaxation (what opens up?) and tightening (what
new structure is exposed?).

**Prompt.** Enumerate the constraints surrounding the current node
(data availability, compute budget, time, audience, API, symmetry
assumptions, regulatory, …). For each: (1) relax it — what becomes
possible? (2) tighten it — what new requirement appears? Emit ≥ 2
children — one relax, one tighten.

**Per-preset flavor:**

- **brainstorm.** "Relax: drop the cosmological-prior constraint on
  Σ_crit → opens a model-independent SNR_resolved approach.
  Tighten: assume not just Λ-CDM but a specific bispectrum prior →
  exposes a new degeneracy between f_NL and substructure mass
  spectrum."
- **attack.** "Relax: the paper's S/N criterion required 5σ. At
  3σ, half the reported detections drop out — what does the
  remaining sample look like? Tighten: at 7σ, the result strengthens
  but the sample size halves — was the 5σ choice optimized
  post-hoc?"
- **design.** "Relax: drop the 99.9% uptime SLO → opens a much
  simpler single-region architecture. Tighten: 99.99% SLO requires
  multi-region active-active, which the current proposal doesn't
  support."
- **code-audit.** "Relax: support files > 100MB → exposes that
  [upload.py:42](#L42) loads the entire file into memory before
  hashing. Tighten: support files < 1KB → exposes a different bug
  where the streaming path skips magic-byte sniffing entirely."

**Output.** ≥ 2 children (one relax, one tighten) with the changed
constraint named in field-5 `assumptions` of each.

---

## §3.F — Scale extrapolation

**Purpose.** Push the node's operating regime by orders of magnitude
in either direction (and into domain boundaries) to expose
regime-specific failures or opportunities.

**Prompt.** The node operates at scale S (in whatever dimension is
natural — load, signal-amplitude, data size, redshift, latency
budget, user count, …). What happens at 1000× S? At 0.001× S? At a
domain boundary (Planck scale / cosmological scale / single-particle
/ unbounded user growth / 0-user case)? Emit ≥ 1 child for the
extrapolation that exposes new physics / behavior.

**Per-preset flavor:**

- **brainstorm.** "Substructure detection currently targets
  ~10⁸ M_sun. Push to 10¹¹: solar-mass halos approach galaxy-cluster
  range, the regime where stellar gravitational lensing dominates.
  Push to 10⁵: subhalos in the warm-dark-matter cutoff regime —
  potentially a WDM constraint angle."
- **attack.** "Method validated at z < 0.5. Extrapolate to z > 2:
  the photometric SNR drops to where the §3 noise model becomes
  invalid; the paper claims no extrapolation but Fig. 7's
  z-evolution panel implicitly does."
- **design.** "Current design assumes 10K daily-active users.
  Extrapolate to 10M: the synchronous JWT-verification call to the
  auth-service becomes the system bottleneck. Extrapolate to 10
  (during onboarding): caching is irrelevant; the design should
  optimize for first-request latency instead."
- **code-audit.** "[upload.py:42](#L42) tested with single-user
  load. Extrapolate to 1000 concurrent uploads: the in-memory hash
  computation triggers OOM. Extrapolate to upload-of-size-0: edge
  case not handled — empty file gets stored with a corrupted hash."

**Output.** ≥ 1 child branch focused on the most-revealing
extrapolation, with the new regime explicitly named.

---

## §3.G — Substitution

**Purpose.** Replace one major component of the node's structure
(dataset, algorithm, target metric, dependency, audience) and
observe what changes — both what the engine learns from the swap
and what new non-trivial branch the swap opens.

**Prompt.** List the major components of the node's structure
(typically 4–8 items). For each, ask: *"if I swap this for the
nearest plausible alternative, does the node's conclusion still
hold, and does the alternative open a new branch?"*

**Per-preset flavor:**

- **brainstorm.** "Substitute the Halofit nonlinear power spectrum
  with HMcode → does the SNR_resolved estimate change? If yes,
  there's a model-dependence subnode worth exploring."
- **attack.** "The paper used MICE-grand-challenge mocks. Substitute
  with EuclidEmulator2 mocks → would the method's quoted bias
  change? If so, the bias estimate is mock-dependent and the
  paper's robustness claim weakens."
- **design.** "Substitute the proposed Postgres backend with a
  document store (e.g. Mongo) → the relational queries become
  awkward but the multi-tenant schema becomes simpler. Trade-off
  worth surfacing."
- **code-audit.** "Substitute [upload.py:42](#L42)'s SHA-256 with
  BLAKE3 → 3× faster on the hot path. Substitute the bcrypt cost=10
  password hash with Argon2id → meets modern OWASP recommendation."

**Output.** ≥ 1 child branch built around the substitution that
most clearly opens a new structural direction.

---

## §3.H — Office-hours 6Q

**Purpose.** Subject the node to a YC-style 6-question grilling
focused on *demand reality* and *concrete narrowness*.

**Prompt.** Answer each question with hard evidence (not
hand-waving). Each "no good answer" is itself a child branch — the
node's exposure point.

1. **Demand reality.** Concretely, who benefits, and how many?
2. **Status quo.** How do they cope today?
3. **Sharpening.** Narrowest "must, now, for this" slice?
4. **Minimum wedge.** Smallest experiment that validates the whole?
5. **Prior art.** Who's already doing it (`WebSearch` mandatory)?
6. **Future-fit.** Will this matter in 5 years?

Emit ≥ 1 child that either passes all 6 with strength or
explicitly documents a failure point.

**Per-preset flavor:**

- **brainstorm.** "Q1 (demand): substructure detection benefits
  WGL theorists + DM-particle-physicists; ≤ 200 people field-wide.
  Q3 (sharpening): the 'must' is constraining DM particle mass —
  one narrow scientific claim. Q4 (wedge): a single Subaru-HSC
  cluster's secondary-peak detection at 4σ would be the wedge."
- **attack.** "Q5 (prior art): we found Smith et al. (2023, arXiv
  2305.xxxxx) doing essentially the same method 9 months earlier
  — the paper doesn't cite them. This is a major critique."
- **design.** "Q1 (demand): the internal admin tool serves 12
  engineers, none of whom currently asks for SSO. Q3 (sharpening):
  the 'must' is just session-survival across machine restarts —
  not the full SSO scope being proposed."
- **code-audit.** "Q6 (future-fit): the [upload.py:42](#L42)
  handler is in a service we're deprecating in 6 months. Severity
  of the bug doesn't change, but priority does — surfaced as
  context."

**Output.** ≥ 1 child branch surfacing whichever question reveals
the most-actionable weakness or strength.

---

## §3.I — Contrarian

**Purpose.** Surface the node's implicit dependence on ≥ 3
field-mainstream consensuses and explore the regime where one of
them is wrong.

**Prompt.** "What 3 things does the field currently agree on, that
this node relies on?" For each: "in what regime could this
consensus be wrong, and what happens to the node there?" Emit a
child for the consensus most likely to be wrong somewhere.

**Per-preset flavor:**

- **brainstorm.** "Consensus 1: WGL signals are dominated by
  shape-noise. Possible regime where this is wrong: at very large
  scales, cosmic-variance dominates instead. Branch: build a
  scale-dependent noise model and re-derive optimality bounds."
- **attack.** "Consensus the paper relies on: photometric redshift
  errors are well-modeled by a Gaussian convolution. Regime where
  this is known wrong: catastrophic outliers in the SDSS-style
  template-fitting at z > 1.2. Paper's analysis is in that regime;
  cite-and-attack."
- **design.** "Consensus: 'OAuth is the standard for B2B SSO.'
  Regime where this is wrong: the customer is on Active Directory
  and refuses anything but SAML. Branch: a SAML-first variant
  design."
- **code-audit.** "Consensus: 'parameterized queries prevent SQL
  injection.' Regime where this is wrong: dynamic table names that
  aren't parameterizable, like
  [analytics.py:201](#L201). Branch: confirm the table-name
  whitelist is exhaustive."

**Output.** ≥ 1 child branch targeting the consensus most likely
broken in the relevant regime.

---

## §3.J — Failure-driven

**Purpose.** Convert concrete *present* failures (not hypothetical
"could be better") into new research / critique / design / audit
questions.

**Prompt.** List ≥ 3 concrete failures the node currently has —
each anchored to a `file:line`, Fig. N, or command-output mismatch.
For each: "is this failure itself a question worth asking?"

**Per-preset flavor:**

- **brainstorm.** "Failure: our current pipeline misses 30% of
  subhalos in the 10⁹–10¹⁰ M_sun range (Fig. 3 of latest report).
  This isn't 'could improve' — it's a specific quantified gap. New
  branch: a sub-direction targeted at exactly this mass bracket
  with a tailored detection scheme."
- **attack.** "Failure observed in the paper's Fig. 5: the
  reconstruction breaks at SNR < 3 with no acknowledgment in the
  caption or body. Critique: the paper's stated 'robust across all
  SNR' is mechanically false; revise or add caveat."
- **design.** "Failure observed in current admin tool: session
  expires every 30 minutes, killing in-progress work. Concrete
  failure-count: 4 angry Slack messages this week. New branch:
  prioritize session-survival over the proposed scope expansion."
- **code-audit.** "Failure observed: production logs show
  [upload.py:42](#L42) raising `MemoryError` 12× in the last
  month, always on files between 80–100MB. Specific gap, not
  hypothetical. Branch: streaming-hash path is the fix."

**Output.** ≥ 1 child branch built around the most-actionable
present failure.

---

## §3.K — High-risk asymmetric payoff

**Purpose.** Force exploration of ≥ 3 candidate branches whose
expected value is dominated by a small probability of *paradigm-level*
success. Pick the most-concrete and derive it fully.

**Prompt.** What 3 branches, if successful, would represent a
qualitative jump (not an incremental win) for the node? Most will
be `DEAD-END` after full derivation, but the value is in having
explored. Skipping this framing is forbidden (engine §F4).

**Per-preset flavor:**

- **brainstorm.** "High-risk 1: a direct detection of an individual
  subhalo via its time-varying lensing signature on a single
  background galaxy. If true, single-handedly resolves WDM vs
  CDM. Low probability of feasibility (microlensing-style
  sensitivities required), but worth full derivation to bound the
  observability requirements."
- **attack.** "High-risk fatal critique: the paper's central
  result depends on a numerical constant that, traced through the
  pipeline, comes from a typo'd CSV cell. If true: full retraction
  needed. Derive the trace; if the constant is in fact correct,
  fall to REFUTED. Either way, the audit value is high."
- **design.** "High-risk: abandon the proposed framework entirely
  and switch to a managed service (e.g. Workspace/Clerk + Workato
  for the workflow piece). If the customer accepts a vendor lock-in
  trade we hadn't considered, this is 5× faster to ship and 10×
  cheaper to maintain. Derive the customer-conversation needed."
- **code-audit.** "High-risk: not 'a buffer overflow', but 'the
  authentication entirely bypassable through HTTP header
  smuggling against the load-balancer'. Concrete steps to test:
  craft a `Transfer-Encoding: chunked\r\nContent-Length: 0`
  request and observe the downstream behavior. If exploitable,
  critical CVE-class finding."

**Output.** ≥ 1 fully-derived child branch (§4 all 12 fields)
even if the verdict lands at `DEAD-END` / `REFUTED` /
`NOT-RECOMMENDED`. Placeholder branches dropped in for compliance
do NOT count.

---

## §3.L — Meta (LLM blind-spot self-audit)

**Purpose.** Catch the engine's own habit of producing
training-distribution-shaped output.

**Prompt.** Self-audit, 7 questions, treated as forced
introspection (not a checkbox):

1. **Distribution check.** Are all my branches from
   training-distribution-frequent framings (the things LLMs say
   often)? What framings are *uncommon* in this field but a human
   expert would expect?
2. **Writable vs important.** Have I confused "what I can produce
   smooth prose about" with "what's actually important"?
3. **LLM-rare-but-human-obvious.** What's something a senior
   human expert in this field would immediately say but LLM
   training data is thin on?
4. **Smoothness check.** Is my output too rhetorically smooth?
   Real research / critique / design discussions are *rough*,
   contradictory, partial. Where am I being suspiciously
   coherent?
5. **Math-heavy branches.** Am I avoiding branches that require
   real symbolic derivation / numerical simulation? Add one.
6. **Implementation-heavy branches.** Am I avoiding branches that
   require running code / fetching data / doing experiments? Add
   one.
7. **Weirdness check.** Is the *weirdest* branch in the tree
   actually weird, or just dressed-up safe? Force another if not.

**Per-preset flavor:**

- **brainstorm.** "Self-audit reveals: I've been generating
  signal-detection branches (training-frequent) but no
  data-acquisition / instrument-design branches (training-rare,
  human-obvious). New child: 'what telescope-time-allocation
  proposal would best test direction X?'"
- **attack.** "Self-audit: I've been generating
  statistical-criticism branches (LLM-frequent) but no
  presentation-quality / figure-readability branches that a
  reviewer would actually write in a real report. New child:
  attack on the typography / color choices in Fig. 6 that obscure
  the main result."
- **design.** "Self-audit: I've been producing
  framework-comparison branches but no 'who-builds-it' branches.
  New child: 'what's the smallest team that can own this for 3
  years?'"
- **code-audit.** "Self-audit: I've been finding standard CWE
  patterns but no 'who-can-exploit-this' branches. New child:
  threat model — under what attacker capabilities (insider /
  authenticated user / unauthenticated / network-level) does the
  finding matter?"

**Output.** ≥ 1 child branch sourced from the audit's
blind-spot list. This must be a *new* branch, not a rephrase of
something already in the tree.

---

## §3.X — External resource cross-check (per node, unless `--no-online`)

**Purpose.** Verify the node against external state — literature,
repositories, datasets, tools, prior criticism — that might have
already done related work or expose related problems. **What to
search for is preset-determined** (see flavor below): a brainstorm
node hunts for prior art and invocable tooling; an attack node hunts
for published critiques and errata of the artifact's claims. Using
the wrong query set (e.g. searching for "langchain tool" while
auditing a paper) wastes the pass.

**Steps.**

1. `WebSearch` with the preset-appropriate query set (see
   **Per-preset flavor**). Always include `<node subject> arxiv` /
   `<subject> github` as a baseline; add the preset's specialized
   queries on top.
2. For each promising hit, `WebFetch` the actual page (not the
   snippet) to confirm the content matches the search description —
   a `WebSearch` snippet is never sufficient on its own (§F1).
3. Append findings to the node's §4 external field
   (`external_resources` for brainstorm/design, `external_check` /
   `related_findings` for attack/code-audit) with URL + one-line
   description.

**Per-preset flavor:**

- **brainstorm.** Prior art and *invocable tooling*: `<subject>
  arxiv` / `<subject> github` / `<subject> dataset` / `<subject>
  benchmark`, plus `<subject> claude code plugin` / `<subject> mcp
  server` / `<subject> langchain tool`. Goal: "has someone built
  this, and can I reuse it?"
- **attack.** *Published criticism of the artifact's claim*: `<claim
  keywords> erratum` / `<claim> arxiv comment` / `<claim> reply` /
  `<method> failure mode` / `<method> irreproducible`. Also
  `WebFetch` the artifact's own cited prior work to confirm it
  actually says what the artifact claims — a misrepresented citation
  is a high-severity critique.
- **design.** *Production post-mortems and pattern trade-offs*:
  `<pattern> architecture tradeoffs` / `<pattern> postmortem` /
  `<vendor/service> limits` / `<pattern> at scale`. Goal: "who
  shipped this and what bit them?"
- **code-audit.** *Known vulnerabilities and advisories*:
  `<dependency> CVE` / `<dependency> advisory` / `<pattern> CWE` /
  `<library> <version> security`. Also cross-`Grep` the repo for the
  same pattern elsewhere (feeds `related_findings`).

**Output.** Append the verified findings to the node's external
field. `--no-online` mode skips steps 1–2; tag the node
`external_resources_unchecked=true` (§6 convergence still expects
the tag — it's not a free pass).

---

## Notes on running the framings

### Sequence vs parallelism

- For nodes with expected width ≥ 5 children (common at the root
  and for hot leaves), the 12 framings can be run in parallel by
  dispatching each to an `Agent(Explore)` sub-agent. Each sub-agent
  gets the node's §4 fields + the framing prompt + the preset's
  flavor examples. Main agent merges results and does §4 + §5.
- For smaller widths (deep in the tree where most leaves are
  marginal), sequential is fine — the framings themselves are
  cheap; the cost is in the §4 derivation that follows.

### Per-framing failure modes

- **A** "every assumption looks load-bearing; can't remove any" →
  the node's `assumptions` field is underspecified; go back to §4
  and surface more assumptions.
- **B** "inversion is trivial / vacuous" → either the node is at
  a domain boundary where inversion isn't well-defined (declare
  so and move on), or the node's subject is too vague (sharpen).
- **C** "no cross-field has a similar problem" → genuine
  possibility; check ≥ 3 fields with care before declaring.
  Negative result is fine and informative.
- **D** "the strongest counter is weak" → suggests the node is
  robust; this is itself useful evidence, but verify by trying ≥ 2
  more counter-stances before declaring.
- **K** "can't think of a high-risk branch" → forbidden conclusion
  (§F4). Force yourself; the value is in *trying*, even if all 3
  candidates land DEAD-END after full derivation.
- **L** "self-audit shows nothing" → forbidden conclusion. The
  audit is meant to be uncomfortable; if it isn't, you're going
  through the motions. Re-do with harder questions.

### Calibration across rounds

In round N+1, when re-expanding an `advances` leaf, the engine
*should* observe diminishing returns — the `convergence_metric`
ratio should drop. If it doesn't, either the framings are
hitting genuinely fertile territory (good — keep going) or the
engine is generating pseudo-divergent variants of the parent
(bad — apply §F2 + §5.4 merging more aggressively).
