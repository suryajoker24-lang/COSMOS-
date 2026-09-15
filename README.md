# COSMOS — AI Exoplanet Detection for Kepler Light Curves

COSMOS is an end-to-end research workstation for detecting and characterising transit-like signals in Kepler photometry. The repository combines a scientific Python pipeline, a FastAPI service, a browser dashboard, candidate vetting, NASA/MAST cross-validation, and competition-submission tooling.

> **Scientific status:** COSMOS is a research/competition system, not a claim that every detected signal is a confirmed exoplanet. Candidate confidence and NASA validation are separate concepts.

## Architecture

```text
CSV / Parquet / FITS
        │
        ▼
Data ingestion + schema validation
        │
        ▼
Quarter normalisation / quality filtering
        │
        ▼
Transit-preserving detrending
        │
        ├───────────────┐
        ▼               ▼
      BLS search      optional GP / TLS confirmation
        └───────┬───────┘
                ▼
Candidate refinement + features
                ▼
Physics vetting
  ├─ odd/even consistency
  ├─ secondary-eclipse checks
  ├─ recurrence / coverage
  └─ systematic-artifact checks
                ▼
Candidate ranking + confidence calibration
                ▼
Star-level result / API / submission CSV
                │
                └── optional independent NASA/MAST validation
```

## Repository layout

```text
COSMOS/
├── backend/                 # FastAPI service and ASTRA assistant
│   ├── main.py
│   ├── schemas.py
│   ├── jobs.py
│   ├── database.py
│   ├── detect.py
│   ├── pipeline_runner.py
│   └── astra/
├── src/                    # Scientific detection core
│   ├── data/
│   ├── preprocessing/
│   ├── detrending/
│   ├── search/
│   ├── candidates/
│   ├── features/
│   ├── vetting/
│   ├── models/
│   ├── calibration/
│   ├── validation/
│   └── submission/
├── pipeline/               # Compatibility/service pipeline modules
├── app/                    # CLI entry point
├── frontend/               # Browser application assets
├── scripts/                # Training, evaluation, audit and validation scripts
├── models/                 # Trained artifacts (keep secrets/private data out)
├── results/                # Generated outputs (not source data)
├── tests/                  # Automated tests
├── docs/                   # Scientific and architecture documentation
├── pyproject.toml
├── requirements.txt
├── Dockerfile
└── docker-compose.yml
```

## Quickstart

Python 3.11+ is recommended.

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
```

### Analyze one light curve

```bash
python -m app.cli analyze --input path/to/star.parquet
```

### Batch analysis

```bash
python -m app.cli batch --input path/to/lightcurves --output results/batch.csv
```

### Train / evaluate

```bash
python -m app.cli train
python -m app.cli evaluate --split dev
```

### Competition submission

For the AstroBit challenge, the private set contains **87 stars**. Generate the submission from the private data only after the final pipeline has been evaluated and independently sanity-checked:

```bash
python -m app.cli submission \
  --input data/raw/private_pack/private \
  --output submission_cosmos.csv

python -m app.cli validate submission_cosmos.csv
```

The required columns are:

```text
star_id,prediction,confidence,period,depth_ppm,duration_hours
```

For `prediction=0`, characterization fields should remain blank. Do **not** use a pre-generated diagnostic CSV as a competition submission without validating its scientific quality.

## API

Start the service with:

```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

Useful endpoints include:

- `GET /health`
- `GET /api/metrics`
- `GET /api/stars`
- `GET /api/stars/{star_id}`
- `GET /api/lightcurve/{star_id}`
- `POST /api/analyze/star`
- `POST /api/analyze/batch`
- `GET /api/candidates`
- `POST /api/submission`

The API should report real pipeline errors rather than silently replacing failed analysis with fabricated candidate data.

## Scientific validation

NASA/MAST cross-validation is an **independent validation layer**, not a source of challenge labels. A challenge target that cannot be mapped to a canonical KIC must remain `UNVERIFIED`; absence of a NASA record must not be treated as evidence of a conflict.

See `NASA_VALIDATION_REPORT.md`, `SCIENTIFIC_METHOD.md`, `DATA_AUDIT.md`, and `ARCHITECTURE_AUDIT.md` for the current methodology and limitations.

## Reproducibility

Analysis runs should record the input identity/hash, pipeline version, configuration, execution time, and candidate-level diagnostics. Do not commit private challenge data, credentials, `.env` files, virtual environments, caches, or generated database files.

## Disclaimer

A transit-like periodic dip is not by itself proof of an exoplanet. COSMOS reports candidates and evidence; scientific confirmation requires additional validation and, where appropriate, follow-up observations.
