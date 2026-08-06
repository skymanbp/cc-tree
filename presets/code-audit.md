---
name: code-audit
description: Code-flavored adversarial review tree. Each node is one code-audit finding (security / performance / correctness / contract violation / data integrity); 12 framings attack the code from multiple reviewer / attacker perspectives; every leaf resolves to CONFIRMED (file:line evidence + proposed_fix + optional PoC) / REFUTED (code already handles) / MARGINAL (depends on threat model or deployment context). Hard ban on NEEDS-MORE-INFO leftover. Differs from attack preset in §3 framing flavors (threat-modeling angles) and node schema (adds exploit_path + mitigation_present fields).
use-when: |
  - User says "code audit" / "security review" / "审代码" /
    "review this file" / "find bugs" / "what could go wrong here"
  - User wants adversarial review of a code file / directory / PR
  - User wants surface security / perf / correctness issues a
    static linter would miss

root_kind: code

subject_label: finding

verdict_enum:
  advances: CONFIRMED
  kept:     MARGINAL
  pruned:   REFUTED
  blocked:  INCOMPLETE_FORBIDDEN

convergence_metric: advances

score_dims:
  - {key: S, name: severity,           desc: "Impact if exploited / triggered. 0=cosmetic, 1=minor (UX bug), 2=substantive (data loss / DoS at scale), 3=critical (auth bypass / RCE / arbitrary data exfiltration)."}
  - {key: P, name: position-specificity, desc: "Localization precision. 0=vague 'codebase has issues', 1=function-level, 2=line-range, 3=specific file:line + minimal reproducible example."}
  - {key: R, name: reproducibility,    desc: "Can the issue be reproduced reliably? 0=requires unknown trigger, 1=conditions partly known, 2=clear repro steps documented, 3=runnable PoC included."}
  - {key: F, name: fixability,         desc: "Cost of the fix. 0=architectural (rewrite a module), 1=non-trivial refactor, 2=local change ≤ 20 lines, 3=one-line change with clear justification."}
  - {key: X, name: exploit-likelihood, desc: "Probability the issue actually gets triggered / exploited in the wild given the deployment context. 0=requires unlikely attacker capabilities, 3=triggered by routine input."}

node_schema:
  - finding_statement       # 1: ≤ 3 sentences naming the issue
  - parent_framing          # 2: §3.A–§3.L
  - code_position           # 3: file:line range + Read-verified quoted excerpt
  - root_cause              # 4: full causal chain — why does the code allow this? what assumption breaks?
  - assumptions             # 5: ≥ 3 premises (attacker capabilities, deployment context, dependency versions)
  - exploit_path            # 6: how to trigger / exploit, in ≥ 3 ordered steps; runnable PoC where feasible
  - mitigation_present      # 7: Grep+Read across module + nearby tests; "no mitigation in <files checked>" or quoted mitigation excerpt
  - alternative_interpretations # 8: ≥ 2 "maybe I'm wrong" paths, each tested against the code
  - proposed_fix            # 9: concrete patch (diff-ish prose: "change line 42 from X to Y because Z") with rationale
  - threat_model_context    # 10: under what attacker capabilities / deployment scenarios does this matter? (insider / network / supply-chain / etc.)
  - related_findings        # 11: §3.X + cross-file Grep for the same pattern elsewhere; URLs to CVE / advisory if known issue
  - verdict_provisional     # 12: CONFIRMED / MARGINAL / REFUTED / INCOMPLETE_FORBIDDEN

output_artifacts:
  primary: findings.md      # CONFIRMED findings, sorted by severity × exploit-likelihood desc
  secondary:
    marginal: marginal.md   # MARGINAL — context-dependent (e.g. only matters with privileged attacker)
    refuted: refuted.md     # REFUTED — code already mitigates; positive record

glossary_paths:
  - SECURITY.md
  - THREAT_MODEL.md
  - CLAUDE.md
  - .github/CODEOWNERS
---

# code-audit preset

This preset configures the universal `tree` engine for **adversarial
code review**. Use when there's a code file / directory / PR and
the user wants findings that a typical static linter / SAST tool
would miss.

## §2 baseline (code-audit-specific)

For each `<root>` (a file or directory path):

1. **Full code read.**
   - If file: `Read` the whole file. If > 2000 lines, chunk-Read
     with offset/limit until full coverage.
   - If directory: `Glob <dir>/**/*.{py,js,ts,go,rs,...}` (extension
     inferred from primary language in the dir); `Read` every file
     ≤ 500 lines fully; spill larger ones via offset/limit.
2. **Adjacent tests + fixtures.** `Glob` `tests/**/<target-name>*`
   or `__tests__/**`; `Read` the most relevant ≤ 5 test files.
   This tells the engine what the code is *expected* to handle.
3. **Recent change context.** `Bash git log --oneline --follow
   <target>` for the last 20 commits — find recent rewrites,
   security-relevant changes, mentions of CVEs / advisories.
4. **Project security conventions.** `Read` (if present)
   `SECURITY.md` / `THREAT_MODEL.md` / `.github/CODEOWNERS` /
   `CLAUDE.md`. These tell the engine what's already considered.
5. **Dependency surface.** `Grep "^import\|^from\|require\|use "
   <target>` (language-appropriate); list every external
   dependency with its version (from `requirements.txt` /
   `package.json` / `Cargo.toml` / `go.mod`).
6. **Root node fields (6):**
   - **target_summary**: 1 sentence describing what the target
     does (in user-observable terms, not "imports modules and
     defines functions")
   - **entry_points**: enumeration of public functions / methods /
     HTTP routes / CLI commands / IPC handlers
   - **inputs_from_caller**: parameter types + whether validation
     is present (yes / partial / no, with file:line)
   - **external_dependencies**: libraries / services / files / env
     vars + their versions
   - **threat_surface**: list of threat categories applicable (auth
     bypass / injection / data leak / DoS / race condition / etc.)
     with rationale
   - **deployment_context**: best-known info about where the code
     runs (production-facing? CI-only? internal-only? library?)

If `target_summary` or `entry_points` are empty (target is
unparseable / not actually code), **stop** with
`EARLY_STOP=root_underspecified`.

## §3 framing flavors (code-audit-specific)

The 12 framings translate to security/perf/correctness contexts:

- **§3.A First-principles.** Strip an assumption ("the input
  string length is bounded"); does the code still work? Most
  injection bugs come from violated implicit assumptions.
- **§3.B Inversion.** Pick a "happy-path" branch; explore the
  error / unhappy-path branch. Most defensive-coding gaps are in
  the unhappy path.
- **§3.C Cross-disciplinary reviewer.** Adopt each of:
  - database engineer (transactionality / index strategy / data
    integrity)
  - distributed-systems engineer (idempotency / partial failure /
    retries / clock skew)
  - security engineer (OWASP top 10 / CWE pattern / threat model)
  - performance engineer (allocations / N+1 queries / lock
    contention)
  - SRE (observability / on-call burden / failure modes)
  - reviewer of human factors (API ergonomics / error messages)
- **§3.D Adversarial / red team.** At each layer:
  - unauthenticated outsider
  - authenticated low-priv user
  - authenticated high-priv user gone rogue
  - supply-chain attacker (malicious dependency)
  - compromised CI / build pipeline
- **§3.E Constraint variation.** Relax: support 1000× current
  input size → what breaks? Tighten: input size of 0 / 1 / max →
  edge case missed?
- **§3.F Scale extrapolation.** Concurrent load × 1000? Latency
  budget × 0.01? File size × 1000? Number of users × 1000? Find
  the load shape that breaks the code.
- **§3.G Substitution.** Replace one dependency (DB / cache /
  serialization library) → does correctness still hold? Often
  surfaces "we used to use X, the comments still imply X
  semantics, now we use Y".
- **§3.H Office-hours 6Q.** Especially Q5 (prior art — is there
  a known CVE for this pattern?) and Q6 (future-fit — will this
  code be in service in 5 years? affects fix priority).
- **§3.I Contrarian.** "Parameterized queries prevent SQL
  injection — except table names" / "TLS protects data in
  transit — except behind an unencrypted load balancer". Find the
  consensus this code implicitly depends on and probe where it's
  wrong.
- **§3.J Failure-driven.** Look at production logs (if `Bash`able)
  / recent incident reports / open issues in the repo. Concrete
  past failures → new findings.
- **§3.K High-risk asymmetric.** Don't stop at "buffer overflow"
  — go to "authentication entirely bypassable via header
  smuggling against the LB". Most will be REFUTED after
  derivation; the high-severity ones are the highest-EV findings.
- **§3.L Meta (LLM blind-spot self-audit).** Specifically:
  1. Am I generating standard CWE-pattern findings only? What's
     project-specific?
  2. Am I avoiding findings that require running the code (only
     reading)? Force one.
  3. Am I avoiding findings that require multi-file context?
     Force one.
  4. Is the threat-model context being applied or am I just doing
     generic security review?

## Verdict mapping detail

- **REFUTED first.** If `mitigation_present` shows the code
  already addresses the finding (or a defense-in-depth elsewhere
  makes it inaccessible), verdict is **REFUTED** regardless of
  severity. Document in `refuted.md` as a positive record.
- `score ≥ 11` AND `mitigation_present = empty/insufficient` AND
  `exploit_likelihood (X) ≥ 1` → **CONFIRMED**
- `8 ≤ score ≤ 10` OR `X = 0` (only theoretical) → **MARGINAL**
  (context-dependent)
- `score ≤ 7` → **REFUTED** (this preset's `pruned` role; `DEAD-END`
  is `brainstorm`'s label and is not in this `verdict_enum`). Kept in
  `tree.md`; only findings the code was actually shown to mitigate go
  in `refuted.md`.
- Any field with `[NEEDS_VERIFICATION]` →
  **INCOMPLETE_FORBIDDEN** (engine must drive to a terminal
  verdict before §6 convergence; cannot leave NEEDS-MORE-INFO)

## CONFIRMED-without-PoC is allowed but downgraded

A CONFIRMED finding *should* have a runnable PoC in `exploit_path`,
but if construction is genuinely unsafe (would cause data loss in
production) or requires capabilities the engine doesn't have, a
clear path-to-PoC is acceptable; score's R dimension drops to ≤ 2.

## Preset anti-patterns (additional)

- ❌ Generic CWE pattern matches without applying threat-model
  context. "This might be SQL injection" → `score.X = 0` if the
  surrounding code shows the input is from a trusted-internal
  source.
- ❌ Reporting findings without checking `mitigation_present`
  across ≥ 5 nearby files / module boundaries — many findings are
  actually defended-in-depth.
- ❌ Skipping `exploit_path` because "obvious" — force the steps;
  if the steps require the engine to acquire credentials / make
  unsafe requests, document the path-to-PoC and downgrade R.
- ❌ Treating a finding as confirmed because it matches a well-known
  CWE pattern without verifying the project-specific assumptions
  hold (e.g. the project actually IS exposed to that input).
- ❌ Recommending a fix without `proposed_fix` showing the actual
  diff-ish change — "use a parameterized query" is not actionable;
  "replace line 42's `f-string` with `cursor.execute(sql, params)`
  using params=(user_id,)" is.

## Suggested invocations

```bash
# Audit one file
/cc-tree:code-audit ./src/api/upload.py

# Audit a directory
/cc-tree:code-audit ./src/auth/

# Audit + join with a security policy doc
/cc-tree:code-audit ./src/api/ --glossary ./SECURITY.md

# Capped quick run
/cc-tree:code-audit ./src/api/upload.py --width 15 --depth 2
```

## What "done" looks like

- `<out>/findings.md` — CONFIRMED findings sorted by severity ×
  exploit-likelihood; for each: position, root cause, exploit
  path, proposed fix.
- `<out>/marginal.md` — context-dependent findings (matters if
  threat model includes X).
- `<out>/refuted.md` — code-already-handles cases.
- `<out>/tree.md` / `tree.json` — full audit trail.
- `REPORT.md` with §F8 self-audit (zero INCOMPLETE_FORBIDDEN).
