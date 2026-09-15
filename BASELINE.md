# Baseline Pipeline Performance & Diagnostic Report

## 1. Overview of Starter Pipeline
The starter pipeline implements a minimal baseline consisting of:
1. **Cleaning**: Strict quality mask (`quality == 0`), per-quarter division by median flux, and a fixed 1.0-day centered running median filter.
2. **Search**: Coarse-to-fine Box Least Squares (BLS) over 20,000 log-spaced periods from 3.0 to 400.0 days (capped at $\text{baseline}/3$), refining top 8 peaks within $\pm 2\%$.
3. **Decision Rule**: Thresholding at $\text{SDE} > 10.0$.
4. **Confidence**: Heuristic logistic squashing: $\sigma(0.4 \cdot (\text{SDE} - 10.0))$.

---

## 2. Dev Set Baseline Benchmark Results

Evaluated across all 89 stars in the development set (`data/dev/`):
- **Total Stars**: 89 (51 Ground Truth Positives, 38 Ground Truth Negatives)
- **Runtime**: 357.1 seconds (~4.01 seconds per star across 8 workers)

| Metric | Starter Baseline | Analysis |
|---|---|---|
| **Precision** | **57.30%** | Poor: High false positive rate on clean stars with stellar noise |
| **Recall** | **100.0%** | Trivial: Detects nearly everything because noise hits SDE > 10 |
| **F1 Score** | **0.7286** | Severely dragged down by poor precision |
| **Average Precision (AP)** | **0.6564** | Uncalibrated SDE ranking fails to separate true transits from noise |
| **ROC-AUC** | **0.5937** | Marginally better than random ranking (0.50) |
| **Period Recovery Rate** | **33.33%** | Only 10 of 30 injected planets had period recovered within 2% |
| **Median Relative Depth Error** | **251.4%** | Running median eats transit troughs, destroying depth accuracy |

---

## 3. Diagnostic Breakdown & Failure Analysis

### 3.1. False Alarms on Stellar Variability
Clean stars without planets frequently exhibit rotational modulation, starspots, and instrumental drifts. A naive running median fails to model these trends accurately, leaving residual oscillatory power that BLS registers as high SDE ($> 10.0$), generating false positive detections on non-planet stars.

### 3.2. Transit Distortion by Running Median
The fixed 1.0-day window is too narrow for long-period Earth analogs (which can have transit durations of 10?16 hours). The running median dips into the transit itself, reducing the measured transit depth to a fraction of the true depth and distorting the transit box shape.

### 3.3. Lack of Physics Vetting
The starter pipeline has zero vetting tests:
- Does not check odd vs. even transit depth differences (cannot distinguish eclipsing binaries).
- Does not test for secondary eclipses at phase 0.5.
- Does not verify quarter-to-quarter recurrence.
- Does not test for sub-harmonics ($P/2, 2P, P/3, 3P$).

---

## 4. Next Steps in Scientific Engine
1. **Adaptive Transit-Preserving Detrending**: Iterative outlier-masked Savitzky-Golay / spline filtering that refuses to pull into transit dips.
2. **Physics Vetting**: Odd/even consistency, secondary eclipse veto, and quarter recurrence verification.
3. **ML Candidate Ranking & Probability Calibration**: LightGBM GBDT trained on rich tabular features with GroupKFold star-level validation and Isotonic calibration.
