# Comprehensive Dataset Audit & Semantics Report

## 1. Star Counts & Split Breakdown
- **Train Stars**: 269 (Folder: `data/train`)
- **Dev Stars**: 89 (Folder: `data/dev`)
- **Private Test Stars**: 87 (Folder: `data/private_test`)
- **Total Dataset Size**: 445 stars
- **Observation Baseline**: ~4 years per star (~50k to ~65k long-cadence points, $\Delta t \approx 29.4\,\text<built-in function min>$)

---

## 2. Label vs Injected Truth Semantics

> [!IMPORTANT]
> **Key Semantic Distinction**:
> - `*_labels.csv` represents the **Real Catalogue Classification Ground Truth** (`prediction` $\in \{0, 1\}$, where 1 indicates a confirmed transiting planet system).
> - `*_truth.csv` represents **Synthetic / Injected Transit Signal Ground Truth** containing exact physical parameters ($P$, $T_0$, $\delta_{\text{ppm}}$, $\tau_{\text{hours}}$, $R_p/R_*$, difficulty band).
> - The model is supervised on detection signals and evaluated against injection truth across difficulty bands without data leakage.

### Train Set Label Distribution (`train_labels.csv`)
- Total labeled stars: 269
- Positive transit hosts (`1`): 67 (24.9%)
- Negative non-transiting stars (`0`): 202 (75.1%)

### Dev Set Label Distribution (`dev_labels.csv`)
- Total labeled stars: 89
- Positive transit hosts (`1`): 21 (23.6%)
- Negative non-transiting stars (`0`): 68 (76.4%)

### Dev Injected Signal Physical Parameter Distribution (`dev_truth.csv`)
- Total injected ground-truth signals: 30
- **Transit Depth ($\delta$)**: Min = 120.7 ppm, Median = 253.5 ppm, Max = 1975.7 ppm
- **Transit Duration ($\tau$)**: Min = 3.12 h, Median = 6.38 h, Max = 13.14 h

---

## 3. Light Curve Cadence & Column Schema
- **Columns**: `time` (BJD - 2454833.0), `flux` (e-/s or SAP relative flux), `flux_err`, `quality` (bitmask integer), `quarter` (integer 0 to 17).
- **Sampling Frequency**: $1 / 29.4244\,\text{min} \approx 48.94\,\text{cadences/day}$.
- **Quality Flag Semantics**: `quality == 0` designates unflagged, high-precision scientific cadences. Non-zero flags mask spacecraft thruster firing, reaction wheel desaturation, Earth/Moon in FOV, and cosmic ray hits.

---

## 4. Scientific Strategy & Detection Protocol
1. **Ingestion & Validation**: Bitmask filter (`quality == 0`), drop non-finite values and negative flux anomalies.
2. **Quarter Level Offset Correction**: Normalize each Kepler quarter independently via robust median scaling ($F / \text{median}(F)$).
3. **Transit-Preserving Detrending**: Apply Wōtan biweight windowing with iterative transit dip masking to protect sub-300 ppm shallow signals.
4. **BLS Search**: Frequency-uniform grid search with `astropy.timeseries.BoxLeastSquares.autoperiod()` across 2 to 400 days.
5. **Candidate Refinement & Vetting**: Windowed cutouts for fast Transit Least Squares (TLS), odd/even depth check, secondary eclipse test at phase 0.5, and single-epoch dominance testing.
6. **Supervised Ranking & Isotonic Calibration**: GroupKFold by Star ID preventing data leakage, outputting well-calibrated posterior probabilities $P(\text{Transit} \mid \mathbf{x}) \in [0, 1]$.
