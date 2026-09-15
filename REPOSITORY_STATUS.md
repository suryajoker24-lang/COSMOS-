# COSMOS Repository Audit

This branch is the cleanup/integration branch for the COSMOS project.

## Changes completed

- README rewritten to describe the scientific workflow, API, submission format, and reproducibility expectations accurately.
- `.gitignore` added to keep private datasets, local databases, credentials, caches, virtual environments, and generated submission artifacts out of the public repository.
- Existing scientific documentation retained rather than replacing it with unsupported claims.

## Source integration status

The uploaded local project contains a newer structured implementation under `backend/`, `pipeline/`, and `src/`, while the public repository currently contains an older/root-level implementation as well. These implementations should not be blindly concatenated: several modules use different import paths and data models.

The safe integration target is:

```text
backend/       FastAPI + ASTRA + job orchestration
src/           canonical scientific engine
pipeline/      compatibility/service layer
app/           CLI
frontend/      browser UI
scripts/       reproducible workflows
models/        trained artifacts (only non-sensitive artifacts)
tests/         automated tests
docs/          scientific documentation
```

Before replacing the root-level implementation, run the complete test/evaluation suite against the uploaded local source and reconcile import paths, model artifacts, and API contracts. This avoids publishing a repository that looks cleaner but no longer executes.

## Scientific integrity

NASA/MAST validation is independent from the challenge prediction pipeline. It must never be used to fabricate labels for anonymized `STAR_####` targets. Missing archival records are `UNVERIFIED`, not `NASA CONFLICT`.

Competition submission files must be generated from the final evaluated pipeline and validated against the official six-column format before upload.
