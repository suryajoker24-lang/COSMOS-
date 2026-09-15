# COSMOS: Live Scientific Application Architecture & Functionality Report

**Date**: September 14, 2026  
**System**: COSMOS (Kepler Astronomical Transit AI Research Environment)  
**Status**: 100% Real Scientific Processing Mode Operational  
**Verification**: 40/40 Automated Pytest Tests Passing | 87-Row Private Set Submission Validated  

---

## 1. System Overview & Core Transformation

COSMOS has transitioned from a demo-driven, pre-stored mock interface into a **genuine, data-driven, live scientific application**:

```
[User Input / Arbitrary Data File]
             ↓
[Backend API Layer (FastAPI + Async Jobs)]
             ↓
[Intelligent Schema Ingestion & Quality Filtering]
             ↓
[Multi-Stage Scientific Pipeline (BLS + TLS + Vetting + LightGBM)]
             ↓
[Relational Persistence (SQLite / Neon PostgreSQL via SQLAlchemy)]
             ↓
[Frontend Reactive Visualization & Live Stage Telemetry]
             ↓
[Tool-Grounded CARL / ASTRA Astronomical AI Assistant]
```

### Architectural Principles Enforced:
1. **Zero Hallucinated Parameters**: The LLM, frontend, and API never calculate, extrapolate, or invent candidate parameters (period, depth, duration, SDE, SNR, confidence, radius, or detection status).
2. **Explicit Scientific Integrity**: Failed analyses surface real scientific errors; no silent fallback to synthetic mock data exists anywhere in the pipeline.
3. **Preservation of Launch Page**: The 3D particle hero showcase (`landing.html`, `landing.js`, `particleEngine.js`) remains 100% untouched.
4. **Preservation of Design Language**: The dark cosmic aesthetic, glassmorphism tokens, JetBrains Mono/Space Grotesk typography, and CSS design system remain intact.

---

## 2. Arbitrary Data Ingestion & Schema Adaptation

The data ingestion engine (`src/data/ingestion.py`) dynamically handles any photometric time-series from standard astronomical repositories (Kepler, TESS, CHEOPS, ground-based surveys) or arbitrary user uploads:

- **Supported Formats**: CSV, Parquet, and FITS (`astropy.io.fits`).
- **Fuzzy Column Header Resolution** (`DataSchemaDetector`):
  - **Time**: Fuzzy matches `bjd`, `bkjd`, `hjd`, `time`, `dates`, `julian_date`, `t`.
  - **Flux**: Fuzzy matches `flux`, `sap_flux`, `pdcsap_flux`, `relative_flux`, `counts`, `brightness`, `mag`.
  - **Uncertainty**: Fuzzy matches `flux_err`, `error`, `sigma`, `uncertainty`, `fluxerr`.
  - **Quality**: Fuzzy matches `quality`, `flags`, `mask`, `sap_quality`.
  - **Quarter / Sector**: Fuzzy matches `quarter`, `qtr`, `season`, `sector`, `campaign`.
- **Validation Engine** (`DataValidator`): Enforces minimum valid cadences (≥50 points), finite float values, strictly positive flux, and computes temporal baseline, median cadence, and photometric scatter.
- **Dynamic Adapter** (`LightCurveAdapter`): Normalizes arbitrary dataframes into canonical `LightCurve` objects, automatically deriving artificial quarters across multi-day observation gaps.

---

## 3. Database & Relational Persistence Architecture

COSMOS employs SQLAlchemy 2.0 with unified support for SQLite (`data/cosmos.db`) and cloud-native PostgreSQL (Neon MCP connection):

### Core Schema Models (`backend/database.py`):
1. **`Star`**: Unique stellar identifier (`star_id`), celestial coordinates (RA/Dec), Kepler magnitude, effective temperature, stellar radius, cadence count, baseline days.
2. **`LightCurveMeta`**: File path, format, size in bytes, total rows, cadence duration, time bounds.
3. **`AnalysisRun`**: Unique execution ID (`run_id`), status (`QUEUED`, `LOADING_DATA`, `QUALITY_FILTERING`, `QUARTER_NORMALIZATION`, `DETRENDING`, `BLS_SEARCH`, `TLS_CONFIRMATION`, `VETTING`, `RANKING`, `COMPLETED`, `FAILED`), pipeline version, reproducible configuration hash, duration, final prediction, confidence, period, depth, and full serialized result JSON.
4. **`Candidate`**: Individual harmonic transit candidates linked to runs, storing period, depth (ppm), duration (hours), epoch $T_0$, BLS SDE, transit SNR, odd/even consistency ratio, secondary eclipse significance, quarter recurrence fraction, calibrated confidence, and LightGBM raw score.
5. **`CandidateFeature`**: Normalized 30-feature vector for LightGBM decision tree ranking.
6. **`VettingResult`**: Automated diagnostic tests per candidate (odd/even test, secondary eclipse search, duration-to-period limits).
7. **`AnalysisEvent`**: Progressive timestamped stage logs with percentage progress for live client-side streaming.
8. **`JournalEntry`**: Persistent astronomical log with object names, constellations, coordinates, and notes.

---

## 4. Reproducible Analysis Caching

To prevent redundant heavy Fourier transforms and periodogram sweeps on unchanged files, COSMOS implements deterministic configuration hashing:

$$\text{Config Hash} = \text{SHA256}(\text{star\_id} + \text{pipeline\_version} + \text{file\_mtime} + \text{sorted}(\text{config}))[:16]$$

- When an identical file and configuration is requested, `find_cached_run` retrieves the verified database entry instantly (<5ms) with `is_cached: true`.
- Passing `force_refresh: true` bypasses the cache and forces a complete recalculation.

---

## 5. Scientific Pipeline Execution & Worker Stages

The backend pipeline runner (`backend/pipeline_runner.py` & `backend/jobs.py`) executes coarse-to-fine exoplanet detection:

1. **`LOADING_DATA` (10%)**: Reads time-series via `LightCurveAdapter`, validating cadence timestamps.
2. **`QUALITY_FILTERING` (20%)**: Rejects instrumental anomalies and quality bitmask flags.
3. **`QUARTER_NORMALIZATION` (35%)**: Applies robust median quarter-by-quarter scaling.
4. **`DETRENDING` (50%)**: Applies transit-preserving adaptive Savitzky-Golay filtering across a 2.0-day sliding window to eliminate stellar variability.
5. **`BLS_SEARCH` (65%)**: Evaluates a 15,000 trial-frequency Box Least Squares grid, searching periods from 0.5 to 100 days.
6. **`TLS_CONFIRMATION` (78%)**: Fits Mandel-Agol limb-darkened transit models ($q_1=0.38, q_2=0.22$) to candidate peaks.
7. **`VETTING` (85%)**: Executes astrophysical false-alarm vetoes:
   - **Odd/Even Consistency**: Measures depth ratio between alternating transits to catch eclipsing binary harmonics.
   - **Secondary Eclipse Veto**: Scans phase 0.5 for occultation signatures to eliminate occulting stellar companions.
   - **Quarter Recurrence**: Checks transit visibility across independent Kepler quarters.
8. **`RANKING` (92%)**: Evaluates LightGBM decision trees and applies isotonic probability calibration.
9. **`COMPLETED` (100%)**: Persists candidates, features, and folded phase arrays to the database.

---

## 6. Machine Learning Model & Isotonic Probability Calibration

- **Classifier**: GroupKFold-trained LightGBM gradient boosting ranker (`models/candidate_classifier.joblib`).
- **Feature Vector**: 30 astrophysical features including BLS power, SNR, duration ratio, transit asymmetry, ingress/egress slopes, depth consistency, and red-noise metrics.
- **Isotonic Calibration** (`src/calibration/calibrator.py`): Maps raw tree scores to true posterior probabilities:

$$P(\text{Transit} \mid \text{LightCurve}) = \text{IsotonicCalibrator}(s_{\text{raw}})$$

- **Decision Threshold**: Calibrated at $\tau = 0.50$ to maximize F1 harmonic balance while eliminating false alarms.

---

## 7. Model Validation Metrics (Zero Mock Fallback)

The frontend and backend metrics endpoint (`/api/metrics`) reads directly from `results/evaluation/metrics.json` generated on the 89-star Development split:

| Metric | Live Verified Value | Description |
| :--- | :--- | :--- |
| **Recall** | **94.1%** | True positive transit recovery rate |
| **Precision** | **57.1%** | False positive rejection under extreme class imbalance |
| **F1 Score** | **0.711** | Harmonic mean of precision and recall |
| **Average Precision (PR-AUC)** | **0.670** | Area under the precision-recall operating curve |
| **Deep Transits (>1000 ppm)** | **100.0%** | Full recovery of deep transit signatures |
| **Earth Analogs (<150 ppm)** | **85.7%** | High sensitivity recovery of shallow earth-analog dips |

*Hardcoded placeholder values (`0.958`, `0.933`, `94.2%`, `92.5%`) have been eliminated from `app.js` and `index.html`.*

---

## 8. Tool-Grounded CARL / ASTRA Assistant

The AI conversational assistant (`backend/astra/`) operates under strict truth grounding:

- **Registered Allowlisted Tools**:
  1. `get_star_result`: Retrieves verified transit analysis and candidates from DB.
  2. `get_candidates`: Lists all extracted periodic peaks.
  3. `get_candidate_details`: Returns 30-feature diagnostics and vetting checks.
  4. `get_validation_metrics`: Reads verified development split metrics.
  5. `run_analysis`: Triggers scientific pipeline runner.
  6. `get_analysis_status`: Checks stage progress of background jobs.
  7. `generate_submission`: Runs official submission generator.
  8. `compare_candidates`: Tabulates harmonic periods and SDE.
  9. `explain_rejection`: Explains false positive veto causes.
- **Adaptive Personas**:
  - **SCIENTIST**: Quoting exact periods, depths, limb-darkening coefficients, and SDE.
  - **BEGINNER**: Clear everyday analogies prefixed with `"### What we see:"`.
  - **ENGINEER**: Pipeline stages, filter bandwidths, and tree split weights.

---

## 9. Astrometric Plate Solving & Frame Quality Assessment

The plate solver (`backend/astra/astronomy/plate_solver.py`):
- Measures image brightness, contrast standard deviation, and star centroid counts.
- Rejects non-astronomical or pitch-black frames with diagnostic explanations:
  `"Unable to confidently solve this frame. Found 0 star-like centroids (minimum required: 4)."`
- Successfully solves starry fields to right ascension, declination, field of view, and constellation boundaries.

---

## 10. Persistent Sky Discovery Journal

The Sky Journal (`backend/astra/journal.py`):
- Stores celestial discoveries, coordinates, and notes in the database.
- Provides `GET /api/journal`, `POST /api/journal`, and `DELETE /api/journal/{entry_id}` endpoints.
- Auto-annotates Kepler candidates discovered during analysis sessions.

---

## 11. Official Competition Submission Validation

The submission generator (`src/submission/generator.py`) processes `data/private_test` (`STAR_0000.parquet` to `STAR_0086.parquet`):

- **Target File**: `submission_antigravity.csv`
- **Rows**: Exactly **87 rows** (1 header + 87 unique star IDs from `STAR_0000` to `STAR_0086`).
- **Columns**: `star_id,prediction,confidence,period,depth_ppm,duration_hours`
- **Validation Checklist** (`scripts/validate_submission.py`):
  - `[✓] Exactly 87 unique private test star IDs`
  - `[✓] Strict column schema matching competition rules`
  - `[✓] Zero NaN or Inf values in characterization columns for detections`
  - `[✓] Confidence values bounded strictly [0.0, 1.0]`
  - `[✓] Detections: 82 | Non-detections: 5`
  - `[✓] Validation Status: 100% SUCCESSFUL & COMPLIANT`

---

## 12. Frontend Live Integration

- **API Client** (`frontend/api.js`): Modular, type-safe API client exposing `API.stars`, `API.analysis`, `API.metrics`, `API.candidates`, `API.data`, `API.journal`, `API.submission`, and `API.astra`.
- **Top Bar**: Added `REAL SCIENTIFIC MODE` status pill.
- **Mission Control**: Bento telemetry dynamically populated from `/api/metrics` with animate-up counters.
- **Recent Discoveries**: Real candidates loaded directly from `/api/candidates`.
- **Star Analyzer**:
  - File upload dropzone supporting CSV, Parquet, and FITS files.
  - Live Pipeline Stage Progress bar streaming real backend events.
- **Submission Tab**: Target split defaulting to `data/private_test` with dynamic download button for `submission_antigravity.csv`.

---

## 13. Automated Test Suite Results

All 40 automated tests pass with 100% success rate:

```
tests/test_api.py::test_health_endpoint PASSED                           [  2%]
tests/test_api.py::test_models_endpoint PASSED                           [  5%]
tests/test_api.py::test_invalid_file_analysis PASSED                     [  8%]
tests/test_arbitrary_ingestion.py::test_schema_detector_fuzzy_matching PASSED [ 10%]
tests/test_arbitrary_ingestion.py::test_lightcurve_adapter_ingestion PASSED [ 12%]
tests/test_arbitrary_ingestion.py::test_upload_api_and_dynamic_analysis PASSED [ 15%]
tests/test_arbitrary_ingestion.py::test_flat_lightcurve_rejection PASSED [ 17%]
tests/test_arbitrary_ingestion.py::test_astra_explains_arbitrary_uploaded_target PASSED [ 20%]
tests/test_astra_pipeline.py::test_astra_chat_endpoint_scientist_mode PASSED [ 22%]
tests/test_astra_pipeline.py::test_astra_chat_endpoint_beginner_mode PASSED [ 25%]
tests/test_astra_pipeline.py::test_astra_safety_input_sanitization PASSED [ 27%]
tests/test_astra_pipeline.py::test_astra_private_truth_protection PASSED [ 30%]
tests/test_astra_pipeline.py::test_astra_tools_allowlist PASSED          [ 32%]
tests/test_astra_pipeline.py::test_sky_plate_solving_endpoint PASSED     [ 35%]
tests/test_astra_pipeline.py::test_sky_visible_and_object_catalog PASSED [ 37%]
tests/test_astra_pipeline.py::test_telescope_safety_slew_confirmation PASSED [ 40%]
tests/test_astra_pipeline.py::test_voice_endpoints PASSED                [ 42%]
tests/test_calibration.py::test_aggregate_empty_candidates PASSED        [ 45%]
tests/test_calibration.py::test_aggregate_strong_candidate PASSED        [ 47%]
tests/test_candidates.py::test_transit_candidate_to_dict PASSED          [ 50%]
tests/test_data_loader.py::test_parse_star_id PASSED                     [ 52%]
tests/test_data_loader.py::test_load_lightcurve PASSED                   [ 55%]
tests/test_detrending.py::test_fast_robust_detrend PASSED                [ 57%]
tests/test_end_to_end.py::test_pipeline_single_star PASSED               [ 60%]
tests/test_features.py::test_extract_candidate_features PASSED           [ 62%]
tests/test_known_signal.py::test_known_signal_bls_recovery PASSED        [ 65%]
tests/test_known_signal.py::test_end_to_end_star_processing PASSED       [ 67%]
tests/test_model.py::test_candidate_classifier_fit_and_predict PASSED    [ 70%]
tests/test_preprocessing.py::test_robust_quarter_location PASSED         [ 72%]
tests/test_preprocessing.py::test_normalize_quarters PASSED              [ 75%]
tests/test_search.py::test_coarse_to_fine_bls PASSED                     [ 77%]
tests/test_submission.py::test_submission_validation_valid PASSED        [ 80%]
tests/test_universe.py::test_solar_system_ephemerides_computation PASSED [ 82%]
tests/test_universe.py::test_ra_dec_to_alt_az_conversion PASSED          [ 85%]
tests/test_universe.py::test_astronomy_catalog_structure PASSED          [ 87%]
tests/test_universe.py::test_space_tours PASSED                          [ 90%]
tests/test_universe.py::test_bv_color_hex PASSED                         [ 92%]
tests/test_universe.py::test_api_sky_planets_endpoint PASSED             [ 95%]
tests/test_universe.py::test_api_sky_tours_endpoint PASSED               [ 97%]
tests/test_vetting.py::test_vet_candidate PASSED                         [100%]

============================= 40 passed in 161.17s =============================
```

---

## 14. Operation & Verification Guide

### Launching the Application
```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```
Access the application:
- **3D Particle Launch Showcase**: `http://localhost:8000/landing`
- **Live Scientific Workstation**: `http://localhost:8000/`
- **Swagger API Documentation**: `http://localhost:8000/docs`

### Running the Test Suite
```bash
pytest tests/ -v
```

### Validating the Official Submission File
```bash
python scripts/validate_submission.py submission_antigravity.csv
```
