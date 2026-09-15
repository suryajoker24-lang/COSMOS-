# COSMOS: AI-Based Detection of Earth-Like Exoplanets in Kepler Data

An end-to-end, scientifically rigorous machine learning system for discovering and characterising shallow exoplanetary transits (including Earth analogs) in raw Kepler SAP photometry.

---

## Key Scientific Innovations

1. **Transit-Preserving Adaptive Detrending**:
   - Replaces fixed-window median filtering with multi-pass, outlier-masked Savitzky-Golay filtering.
   - Prevents deep/wide transits (e.g., 10–16 hour Earth analogs) from being absorbed into the baseline.
2. **Frequency-Grid Coarse-to-Fine Box Least Squares (BLS)**:
   - Dynamic period resolution naturally scaling as $\Delta P \propto P^2 / T_{obs}$.
   - Evaluates over 10,000 trial frequencies with Non-Maximum Suppression (NMS) and sub-cadence peak refinement.
3. **Physics-Informed False Positive Vetting**:
   - Odd vs. Even transit depth consistency test (vetoing eclipsing binary contamination).
   - Secondary eclipse search at phase 0.5.
   - Multi-quarter recurrence verification and phase coverage completeness tests.
4. **Candidate-Level Gradient Boosted Tree Ranking (LightGBM)**:
   - Evaluates 15–20 candidates per star.
   - Trains on hard negative candidates from stellar variability and harmonic aliases.
   - Strict `GroupKFold` by Star (zero data leakage).
5. **Calibrated Posterior Confidence & Threshold Optimization**:
   - Out-of-fold Isotonic Regression calibration producing true detection probabilities $p \in [0, 1]$.
   - Star-level candidate aggregation and difficulty-aware threshold tuning.

---

## Project Structure

```
COSMOS/
├── backend/                  # FastAPI Web & API Backend
│   ├── main.py               # REST API endpoints & static mount
│   ├── schemas.py            # Pydantic data schemas
│   ├── jobs.py               # Async background job manager
│   └── astra/                # CARL Scientific Astronomy AI
│       ├── assistant.py      # Core chat & reasoning orchestrator
│       ├── tools.py          # Allowlisted controlled project tools
│       ├── safety.py         # Privacy guard & input sanitization
│       ├── prompts.py        # Adaptive explanation personas
│       ├── providers/        # LLM, STT, and TTS provider abstractions
│       └── astronomy/        # Sky catalog, plate solver, and telescope
├── frontend/                 # Interactive Web UI & Sky Explorer
│   ├── index.html            # Main HTML dashboard & CARL drawer
│   └── app.js                # Live charts, Sky canvas, and Voice handler
├── src/                      # Scientific Core Engine
│   ├── data/                 # LightCurve loading & quality bitmasking
│   ├── preprocessing/        # Quarter-level robust normalisation
│   ├── detrending/           # Transit-preserving adaptive detrending
│   ├── search/               # Frequency-spaced coarse-to-fine BLS
│   ├── candidates/           # Candidate data representations
│   ├── features/             # Tabular transit & noise feature extraction
│   ├── vetting/              # Physics vetting & false positive tests
│   ├── models/               # LightGBM classifier & GroupKFold training
│   ├── calibration/          # Isotonic calibration & star aggregation
│   ├── pipeline.py           # Unified end-to-end detection pipeline
│   └── submission/           # Official submission generator
├── scripts/                  # Command-line workflows
│   ├── run_baseline.py       # Starter baseline benchmark
│   ├── train.py              # Candidate extraction & model training
│   ├── evaluate.py           # Evaluation on Dev set & diagnostic plots
│   └── validate_submission.py# Strict competition CSV validator
├── models/                   # Saved trained models & calibrators
├── results/                  # Benchmark metrics, predictions, & plots
│   ├── baseline/             # Starter baseline metrics & plots
│   └── evaluation/           # Final pipeline metrics & comparison plots
├── tests/                    # Automated pytest test suite
├── Dockerfile                # Production container specification
├── docker-compose.yml        # Multi-container service definition
├── pyproject.toml            # Package metadata & entry points
└── requirements.txt          # Pinned dependency specifications
```

---

## Quickstart & CLI Usage

### 1. Model Training
```bash
python -m app.cli train
```

### 2. Evaluation & Diagnostic Plots
```bash
python -m app.cli evaluate --split dev
```

### 3. Analyze a Single Light Curve
```bash
python -m app.cli analyze --input data/dev/KIC_5306984.parquet
```

### 4. Batch Analysis
```bash
python -m app.cli batch --input data/dev --output results/dev_batch.csv
```

### 5. Generate & Validate Submission
```bash
python -m app.cli submission --input data/dev --output submission_antigravity.csv
```

### 6. Start Web UI & API Server
```bash
uvicorn backend.main:app --port 8000
```
Open `http://localhost:8000/` in your browser.

### 7. Run Test Suite
```bash
pytest tests/ -v
```
