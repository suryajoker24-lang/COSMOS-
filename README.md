# COSMOS — AI Exoplanet Detection for Kepler Light Curves

COSMOS is a reproducible research system for detecting and characterising transit-like signals in Kepler photometry. It combines quality-aware ingestion, quarter stitching, transit-preserving detrending, coarse-to-fine BLS search, optional TLS refinement, statistical vetting, candidate ranking, and a FastAPI interface.

> **Scientific status:** COSMOS reports candidates, not automatically confirmed exoplanets. Detection confidence and archival NASA/MAST validation are separate concepts.

## Scientific workflow

```text
CSV / Parquet
     │
     ▼
quality + finite-value validation
     │
     ▼
quarter-by-quarter robust normalisation
     │
     ▼
Wōtan biweight detrending (median fallback)
     │
     ▼
coarse-to-fine frequency-spaced BLS
     │
     ▼
transit-masked second detrending pass
     │
     ▼
optional narrow-window TLS refinement
     │
     ▼
odd/even + secondary + recurrence + systematic vetting
     │
     ▼
feature extraction + candidate ranking
     │
     ▼
star-level detection + period/depth/duration
```

The long-period search uses frequency spacing rather than a naive fixed period grid, because the required period resolution becomes substantially finer at long periods.

## Repository layout

```text
COSMOS/
├── backend/                 # FastAPI API and detection adapter
├── pipeline/                # Canonical scientific Python package
│   ├── io.py
│   ├── preprocess.py
│   ├── detrend.py
│   ├── search.py
│   ├── refine.py
│   ├── vetting.py
│   ├── features.py
│   ├── models.py
│   ├── model.py
│   ├── gp.py
│   └── submission.py
├── app/                     # CLI
├── scripts/                 # training, evaluation and submission workflows
├── models/                  # optional trained model artifacts
├── tests/                   # regression/unit tests
├── docs/                    # scientific and architecture notes
├── pyproject.toml
├── requirements.txt
└── Dockerfile
```

The `pipeline/` package is now the canonical scientific implementation. The obsolete root-level `pipeline.py` implementation was removed so Python imports cannot silently select two competing pipelines.

## Install

Python 3.11+ is recommended.

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/macOS
# source .venv/bin/activate
pip install -r requirements.txt
```

## Analyze a light curve

```bash
python -m app.cli analyze --input path/to/star.parquet
```

CSV is also accepted:

```bash
python -m app.cli analyze --input path/to/star.csv
```

The result contains the prediction, confidence, characterization fields, candidate diagnostics, runtime, and provenance.

## Train the candidate ranker

Use the dedicated training workflow rather than treating the challenge truth file as a simple star-level label:

```bash
python scripts/train_ranker.py --pack-dir data/raw/train_pack
```

The training workflow keeps stars grouped during cross-validation and distinguishes catalogue positives from injected signals. For injected targets, candidate labels are based on period/alias agreement with the documented injected period.

## Generate a competition submission

```bash
python scripts/make_submission.py \
  --pack-dir data/raw/private_pack/private \
  --team cosmos \
  --out submission_cosmos.csv
```

The generator enforces the six required columns:

```text
star_id,prediction,confidence,period,depth_ppm,duration_hours
```

For `prediction=0`, the three characterization fields are blank. For the 87-star private set, the generator also enforces the expected row count.

## API

```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

Endpoints:

- `GET /health`
- `POST /api/analyze` — upload a CSV or Parquet light curve and run the real pipeline
- `POST /api/analyze/path` — analyze a server-side file path

There is no silent demo-data fallback in these canonical analysis paths. Pipeline failures are returned as failures so they can be diagnosed instead of being mistaken for scientific results.

## Validation and scientific integrity

The challenge data are raw Kepler SAP photometry. The project documentation records the distinction between challenge labels and injected transit truth, and NASA/MAST checks are intended as an independent validation layer rather than a mechanism for fabricating labels.

A periodic dip is not automatically an exoplanet. Robust scientific vetting should include recurrence, odd/even consistency, secondary-eclipse checks, systematics checks, and—when archival metadata permit—centroid/contamination and catalogue cross-matches.

See `SCIENTIFIC_METHOD.md`, `DATA_AUDIT.md`, `ARCHITECTURE_AUDIT.md`, and `NASA_VALIDATION_REPORT.md` for the broader project record.
