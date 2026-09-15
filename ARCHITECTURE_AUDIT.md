# Architecture and Dataset Audit: AI-Based Detection of Earth-Like Exoplanets

## 1. Existing Architecture & Project Context

The project targets automated detection and characterisation of transit signals (with a focus on shallow Earth-sized and Earth-analog exoplanets) in raw Kepler long-cadence SAP (Simple Aperture Photometry) light curves.

### Environment & Technology Stack
- **OS**: Windows (x86_64)
- **Python**: 3.13.5
- **Scientific Computing**: numpy 2.2.6, scipy 1.18.1, pandas 2.3.2, pyarrow 21.0.0, astropy 8.0.1
- **Machine Learning**: scikit-learn 1.9.1, lightgbm 4.7.0
- **Visualization**: matplotlib 3.11.2
- **Web & API Framework**: fastapi 0.115.0, uvicorn 0.30.0, pydantic 2.11.7

---

## 2. Existing Files and Provided Artifacts

| File / Folder | Purpose / Contents | Size / Count |
|---|---|---|
| Problem Statement.pdf | Competition rules, scoring criteria, and scientific priorities | Document |
| Submission Format.pdf | Strict submission schema, scoring formulas, column definitions | Document |
| starter_notebook.ipynb | Baseline pipeline (median filter + coarse-to-fine BLS + threshold) | Jupyter Notebook |
| 	rain_pack/ (	rain/, 	rain_labels.csv, 	rain_truth.csv) | Supervised training set | 269 light curves |
| dev_pack/ (dev/, dev_labels.csv, dev_truth.csv) | Development / validation benchmark set | 89 light curves |
| private/ (target in evaluation) | Final holdout evaluation set | 87 light curves (STAR_0000 to STAR_0086) |

---

## 3. Dataset Structure & Schema Validation

### Parquet Format (Light Curves)
Each star is stored as a Parquet table with ~65,000 to 70,000 rows spanning ~4 years of Kepler primary mission observations (sampled every 29.4 minutes):
- 	ime (loat64): Barycentric Kepler Julian Day (BKJD = BJD - 2454833.0).
- lux (loat32): Raw SAP flux (e-/s), uncorrected for instrumental trends or quarter jumps.
- lux_err (loat32): 1-sigma photon counting / photometric uncertainty.
- quality (int32): Kepler mission quality bitmask (0 = good cadence).
- quarter (int16): Observation quarter index (0 to 17).

### Ground Truth CSVs
1. **	rain_labels.csv / dev_labels.csv**:
   - kepid (int64): Kepler Star ID.
   - label (int64): 1 for known confirmed/candidate Kepler planet host, 0 otherwise.
   - koi_disposition (str): CONFIRMED, CANDIDATE, or NONE.
   - Stellar properties: kepmag, 	eff, logg, 
adius.
2. **	rain_truth.csv / dev_truth.csv**:
   - Injected planet parameters on clean stars: kepid, injected, in, period_days, epoch_t0, depth_ppm, duration_hours, 
p_rs, 
_transits.
   - Difficulty bins: deep, mid, shallow, earth_analog.

### Breakdown
- **Train Set (269 stars)**:
  - 67 stars with native Kepler planets (45 Confirmed, 22 Candidates)
  - 90 stars with synthetic injected planets (20 deep, 25 mid, 25 shallow, 20 earth_analog)
  - 112 clean negative stars
  - Total positives: 157; Total negatives: 112
- **Dev Set (89 stars)**:
  - 21 stars with native Kepler planets (13 Confirmed, 8 Candidates)
  - 30 stars with synthetic injected planets (7 deep, 8 mid, 8 shallow, 7 earth_analog)
  - 38 clean negative stars
  - Total positives: 51; Total negatives: 38

---

## 4. Starter Pipeline Behaviour & Limitations

The starter pipeline demonstrates a minimal end-to-end path:
1. **Cleaning**: Drops quality != 0 cadences; divides each quarter by its median flux; fits a fixed 1.0-day centered running median.
   - *Critical flaw*: A fixed 1.0-day median filter eats or severely distorts wide transits (e.g. 10–15 hr Earth analogs) and introduces ringing around data gaps. In testing, this shrinks recovered transit depth to 30–50% of true depth.
2. **Period Search**: Coarse BLS on log-spaced 20,000 periods from 3 to P_max = baseline/3; takes top 8 peaks and refines +-2% in fine grid of 600 points.
   - *Limitation*: No alias check (P/2, 2P, P/3, 3P); only keeps the single peak with highest coarse SDE; ignores secondary transit signals.
3. **Decision & Vetting**: Single hard threshold on SDE (SDE > 10.0); no ML classification; no odd/even transit vetting; no secondary eclipse check; no quarter recurrence check.
4. **Confidence**: Arbitrary uncalibrated logistic function: 1 / (1 + exp(-0.4 * (SDE - 10))).

---

## 5. Target Scientific Architecture

`
Raw Kepler SAP Light Curve (Parquet)
   |
   v
[ 1. Data Ingestion & Quality Filtering ]
   |- Bitmask filtering (preserve valid transits, reject safe mode/thruster)
   |- Timestamp deduplication, sort, NaN/inf cleaning
   |
   v
[ 2. Quarter-Aware Robust Normalisation ]
   |- Per-quarter robust baseline (Huber/Biweight/Iterative sigma clip)
   |- Discontinuity & gap edge handling
   |
   v
[ 3. Transit-Preserving Adaptive Detrending ]
   |- Iterative biweight / Savitzky-Golay / Spline detrending
   |- Transit masking during trend refitting (preserves shallow depths)
   |- Multi-timescale stellar variability suppression
   |
   v
[ 4. Coarse-to-Fine Search & Multi-Candidate Extraction ]
   |- Period resolution: dP ~ P^2 / (baseline * duration)
   |- Coarse sweep (3d to 400d) -> Peak clustering & Non-Maximum Suppression
   |- Fine local refinement around top 15 peaks
   |- Iterative transit masking for secondary candidate detection
   |
   v
[ 5. Transit Parameter Refinement & Alias Resolution ]
   |- Sub-cadence epoch (T0), period (P), duration (W), depth (delta) refinement
   |- Physical alias checks (P, P/2, 2P, P/3, 3P)
   |
   v
[ 6. Comprehensive Transit Feature Extraction & Vetting ]
   |- BLS & Transit morphology (SDE, SNR, depth, duration, in-transit points)
   |- Odd/Even transit depth difference & shape consistency
   |- Secondary eclipse significance (at phase 0.5)
   |- Quarter recurrence fraction & depth stability across quarters
   |- Systematic period proximity & data-gap correlation
   |
   v
[ 7. Machine Learning Candidate Classifier & Ranker ]
   |- LightGBM Gradient Boosted Trees trained on candidate-level features
   |- GroupKFold by Star (zero data leakage)
   |- Hard negative mining (BLS noise peaks, stellar harmonics, EB aliases)
   |
   v
[ 8. Isotonic Probability Calibration & Threshold Optimization ]
   |- Calibrated confidence in [0, 1] reflecting true posterior probability
   |- Difficulty-aware threshold optimization for max F1 and PR-AUC
   |
   v
[ 9. Star-Level Decision & Submission / API Generation ]
   |- Star-level candidate aggregation
   |- Validated export compliant with competition schema
`

---

## 6. Implementation & Migration Plan

- **Phase 1**: Execute and record Starter Baseline metrics on Train and Dev sets (results/baseline/, docs/BASELINE.md).
- **Phase 2**: Implement core scientific modules (src/data/, src/preprocessing/, src/detrending/, src/search/, src/candidates/).
- **Phase 3**: Implement vetting and physics checks (src/vetting/, src/features/).
- **Phase 4**: Implement ML candidate ranker, GroupKFold validation, calibration, and threshold optimization (src/models/, src/calibration/).
- **Phase 5**: Run rigorous evaluations on dev set across difficulty bands (deep, mid, shallow, earth_analog) and produce diagnostic plots.
- **Phase 6**: Build real FastAPI backend with job queue (backend/).
- **Phase 7**: Integrate interactive web frontend with real light curve, folded transit, and candidate viewers (frontend/).
- **Phase 8**: Build submission generator and automated submission validator (scripts/validate_submission.py).
- **Phase 9**: Final QA, end-to-end integration tests, and documentation.
