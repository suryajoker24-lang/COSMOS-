# Scientific Dependencies, Citations & Attribution

This document details all scientific and core dependencies used throughout the **COSMOS / Exohunter** Kepler exoplanet transit detection engine, including package versions, mathematical purposes, academic citations, licenses, and specific pipeline integration points.

---

## 1. Primary Scientific Libraries

### 1. Wōtan (`wotan`)
- **Version**: `1.10`
- **Purpose**: Transit-preserving robust detrending and stellar variability filtering.
- **Reference / Paper**: Hippke et al. (2019), *"Wōtan: Comprehensive time-series detrending in Python"*, The Astronomical Journal, 158(4), 143.
- **License**: MIT License
- **Exact Integration Point**: `pipeline/detrend.py` — Evaluates robust biweight, pspline, and Savitzky-Golay filtering with iterative 2-pass transit dip masking to protect shallow ($<300\,\text{ppm}$) transit profiles.

### 2. Astropy (`astropy`)
- **Version**: `8.0.1`
- **Purpose**: Broad frequency-uniform Box Least Squares (`astropy.timeseries.BoxLeastSquares`), time coordinate transforms (BJD), and astronomical coordinate utilities.
- **Reference / Paper**: Astropy Collaboration et al. (2022), *"The Astropy Project: Sustaining and Growing a Community-oriented Open-source Python Package for Astronomy"*, The Astrophysical Journal, 935(2), 167.
- **License**: BSD 3-Clause License
- **Exact Integration Point**: `pipeline/search.py` — Executes `BoxLeastSquares.autoperiod()` coarse grid search across $0.5\text{--}400\,\text{days}$ with SDE and harmonic peak filtering.

### 3. Transit Least Squares (`transitleastsquares`)
- **Version**: `1.32`
- **Purpose**: High-sensitivity limb-darkened candidate confirmation, transit parameter refinement, and SNR/FAP calculation.
- **Reference / Paper**: Hippke & Heller (2019), *"Optimized transit detection algorithm to search for periodic transits of small planets"*, Astronomy & Astrophysics, 623, A39.
- **License**: MIT License
- **Exact Integration Point**: `pipeline/refine.py` — Windowed candidate-first TLS on narrow transit cutouts ($\pm 10\text{--}15 \times \tau$, $P_0 \pm 3\%$) avoiding computational bottlenecks.

### 4. celerite2 (`celerite2`)
- **Version**: `0.3.3`
- **Purpose**: Scalable $O(N)$ 1D Gaussian Process modeling for severe correlated stellar noise and rotation terms.
- **Reference / Paper**: Foreman-Mackey et al. (2017), *"Fast and scalable Gaussian process modeling with applications to astronomical time series"*, The Astronomical Journal, 154(6), 220; Foreman-Mackey (2018), RNAAS, 2, 31.
- **License**: MIT License
- **Exact Integration Point**: `pipeline/gp.py` — Transit-masked GP fitting for high-variability stars.

### 5. Lightkurve (`lightkurve`)
- **Version**: `2.6.0`
- **Purpose**: Kepler target structures, quarter handling, phase folding, and astronomical visualization.
- **Reference / Paper**: Lightkurve Collaboration et al. (2018), *"Lightkurve: Kepler and TESS time series analysis in Python"*, Astrophysics Source Code Library.
- **License**: MIT License
- **Exact Integration Point**: `pipeline/io.py`, `pipeline/preprocess.py` — Quarter normalization and phase folding.

### 6. LightGBM & Scikit-Learn (`lightgbm`, `scikit-learn`)
- **Versions**: LightGBM `4.7.0`, Scikit-Learn `1.9.1`
- **Purpose**: GroupKFold cross-validated ranking model and out-of-fold Isotonic Probability Calibration.
- **Licenses**: MIT License (LightGBM), BSD 3-Clause (Scikit-Learn)
- **Exact Integration Point**: `pipeline/model.py` — 23-feature tabular classifier preventing star-level data leakage.

