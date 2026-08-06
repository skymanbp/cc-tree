---
field: physics
description: Senior ApJ/MNRAS/PRD reviewer weighting for physics & astrophysics, with weak-lensing/cosmology flavored concerns, consensuses, failure modes, and evidence bar.
---

# `physics` field profile

> A field profile gives the engine domain-aware reviewer weighting
> (loaded via `--field physics`, see
> [`docs/ENGINE.md` §2.2](../docs/ENGINE.md#22-field-profile-optional---field-namepath)).
> It does **not** relax any universal rule — it only re-prioritizes
> which branches the 12 framings explore first. Every list stays short
> and concrete; a physics reviewer weighs unit consistency and error
> budgets, not vibes.

## Reviewer concerns — feeds §3.C (cross-disciplinary) + §3.D (red team)

What does a senior ApJ/MNRAS/PRD reviewer reliably attack first?

- Dimensional/unit consistency: `h⁻¹ Mpc` vs `Mpc`, comoving vs physical distances, stray factors of `h` in masses and power spectra.
- Error budget quotes only the statistical σ while the dominant systematic (PSF modelling, shear multiplicative bias `m`, additive bias `c`, baryons) is unbudgeted.
- Significance quoted without a look-elsewhere / trials correction for the scanned parameter range.
- Covariance estimated from too few mock realizations with no Hartlap (or Sellentin–Heavens) correction, biasing the inverse covariance.
- Method validated only on the simulation family it was tuned on, with no independent N-body/hydro suite.

## Field consensuses — feeds §3.I (contrarian)

What does the field take for granted that a result might quietly lean on?

- Gaussian likelihood for two-point statistics — breaks at small scales / low S/N where the covariance is non-Gaussian and the estimator is skewed.
- Photo-z posteriors are approximately Gaussian — breaks on catastrophic outliers whose true redshift sits in a secondary mode.
- Shape noise dominates the shear covariance — breaks at large scales / high source density where sample (cosmic) variance takes over.
- A fixed nonlinear `P(k)` fitting formula is adequate — breaks at `k ≳ 0.1–1 h/Mpc` where baryonic feedback shifts power at the 10–30% level.
- Intrinsic alignments are a subdominant additive term — breaks for luminous-red / low-z lens bins where IA rivals the lensing signal.

## Common failure modes — feeds §3.J (failure-driven)

Concrete, recurring ways the work goes wrong in practice.

- An off-by-`h` or comoving/physical mismatch mislabels the x-axis while the code runs clean.
- A Fisher forecast reports unrealistically tight constraints because it fixed nuisances (`m`, photo-z `Δz`, IA amplitude) that should be marginalized.
- Best-fit χ² looks acceptable because the model was fit and evaluated on the same scales, with no held-out check.
- Shear bias calibrated on one image-sim blend density, then applied to data with different blending.
- MCMC chains quoted as final while Gelman–Rubin `R̂` is still far from 1.

## Evidence bar — feeds §3.X (external check) + §4 citations

- Strong: reproduction on an independent dataset/survey/sim suite, a blinded analysis frozen before unblinding, and full-covariance error bars that include the dominant systematics on converged chains.
- Weak (insufficient on its own): a single-realization σ, visual agreement of two curves by eye, χ² on the tuning set, or a forecast with nuisance parameters held fixed.
