# COSMOS Repository Audit

This branch is the cleanup/integration branch for the COSMOS project.

## Completed in this integration pass

- README rewritten around the real scientific workflow and current runnable commands.
- `.gitignore` added to keep private datasets, secrets, caches, virtual environments and generated submissions out of source control.
- A canonical `pipeline/` Python package was added for ingestion, preprocessing, detrending, BLS search, optional TLS refinement, vetting, features, ranking, GP fallback and submission formatting.
- The obsolete root-level `pipeline.py` implementation was removed to eliminate the module/package ambiguity.
- FastAPI `backend/main.py` and `backend/detect.py` now route analysis through the canonical pipeline rather than the old `src.*` implementation.
- A reproducible `scripts/train_ranker.py` workflow was added with star-grouped cross-validation and explicit handling of catalogue labels versus injected transit truth.
- `scripts/make_submission.py` was added for deterministic submission generation.
- Submission validation now enforces the six-column schema, binary predictions, confidence bounds, blank characterization for negatives, and optional expected row count.
- Basic pipeline/submission contract tests were added.
- TLS is declared as an optional refinement dependency.

## Scientific integrity

NASA/MAST validation is independent from the challenge prediction pipeline. It must never be used to fabricate labels for anonymized `STAR_####` targets. Missing archival records are `UNVERIFIED`, not `NASA CONFLICT`.

The challenge specification requires careful treatment of long-period signals, shallow transits, stellar variability, quarter discontinuities, and candidate vetting. The canonical pipeline therefore uses frequency-spaced coarse-to-fine BLS and a transit-masked second detrending pass before optional TLS refinement.

## Remaining engineering work

1. Run the canonical package in a clean Python 3.11 environment with the pinned dependencies.
2. Execute the full train/dev benchmark and compare it against the historical ablation artifacts.
3. Replace any stale UI/API modules that still reference `src.*` paths with the canonical `pipeline.*` API.
4. Add a real end-to-end regression test against a known injected training signal when challenge data are available locally.
5. Keep generated/private results out of the public repository unless deliberately curated as small reproducible artifacts.

Do not claim a leaderboard win from repository structure alone. Scientific performance must be demonstrated by reproducible train/dev evaluation.
