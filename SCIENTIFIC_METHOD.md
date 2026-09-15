# Scientific Methodology & Detection Theory

## 1. Physical Model of Exoplanet Transits

When an exoplanet orbits in a plane aligned with the line of sight to Earth, it periodically occults a portion of its host star's photosphere, resulting in a characteristic dip in observed stellar flux $F(t)$.

### 1.1 Transit Depth and Radius Ratio
The geometric transit depth $\delta$ is related to the planetary radius $R_p$ and stellar radius $R_*$ by:
$$\delta \approx \left(\frac{R_p}{R_*}\right)^2$$
For an Earth-like planet ($R_p \approx 1 R_\oplus$) orbiting a Sun-like star ($R_* \approx 1 R_\odot$), the transit depth is:
$$\delta \approx \left(\frac{6.371 \times 10^6 \text{ m}}{6.957 \times 10^8 \text{ m}}\right)^2 \approx 8.4 \times 10^{-5} = 84 \text{ ppm}$$

### 1.2 Transit Duration
For a circular orbit ($e = 0$) with impact parameter $b = \frac{a \cos i}{R_*}$, the total transit duration $T_{14}$ is governed by Kepler's Third Law:
$$T_{14} = \frac{P}{\pi} \arcsin\left(\frac{R_*}{a} \sqrt{\frac{(1 + R_p/R_*)^2 - b^2}{1 - \cos^2 i}}\right) \approx \frac{P}{\pi} \frac{R_*}{a} \sqrt{(1 + k)^2 - b^2}$$

---

## 2. Light Curve Ingestion & Conditioning

### 2.1 Quality Bitmask Filtering
Kepler long-cadence observations (29.4-minute cadence) record instrumental quality flags. We enforce strict bitmask filtering (`quality == 0`), rejecting cadences contaminated by:
- Reaction wheel desaturation events (momentum dumps)
- Earth/Moon pointings and cosmic ray hits
- Safe mode recoveries and coarse pointing anomalies

### 2.2 Quarter Normalization & Stitching
Kepler's quarterly rolls rotate the spacecraft by $90^\circ$, shifting stellar PSFs across different CCD pixels with varying quantum efficiency and aperture masks. We perform robust quarter-by-quarter median normalization:
$$F_{\text{norm}, q}(t) = \frac{F_q(t)}{\text{median}(F_q)}, \quad \sigma_{\text{norm}, q}(t) = \frac{\sigma_q(t)}{\text{median}(F_q)}$$

---

## 3. Transit-Preserving Detrending

Stellar rotation, starspots, and granulation introduce low-frequency quasi-periodic variations with amplitudes ($10^3 - 10^4\text{ ppm}$) that can completely swamp subtle transit signals ($80 - 500\text{ ppm}$).

### 3.1 Wōtan Robust Biweight Filtering (Hippke et al. 2019)
We employ Tukey's biweight robust estimator using `wotan.flatten()`. The biweight kernel downweights outliers according to:
$$w(u) = \begin{cases} (1 - u^2)^2 & \text{for } |u| \le 1 \\ 0 & \text{for } |u| > 1 \end{cases}, \quad \text{where } u = \frac{F_i - \hat{\mu}}{c \cdot \text{MAD}}$$
By setting the filtering window $\tau_{\text{win}} = 0.75\text{ days} \approx 18\text{ hours}$ (significantly longer than typical planetary transit durations of $2-6\text{ hours}$), high-frequency transit dips are preserved with zero depth distortion while removing stellar trends.

### 3.2 Scalable Gaussian Process Detrending with celerite2 (Foreman-Mackey et al. 2017)
For complex active stars, we support $O(N)$ semi-separable Gaussian Process regression using a Stochastically-driven Simple Harmonic Oscillator (SHO) kernel:
$$k(\tau) = S_0 \omega_0 Q e^{-\frac{\omega_0 \tau}{\sqrt{2}}} \cos\left(\frac{\omega_0 \tau}{\sqrt{2}} - \frac{\pi}{4}\right)$$
The GP is fit to out-of-transit cadences and evaluated over all timepoints.

---

## 4. Signal Search & Period Determination

### 4.1 Astropy BoxLeastSquares (BLS)
The transit detection problem tests the hypothesis of a periodic box-shaped reduction in flux against a constant-flux null hypothesis. Astropy's `BoxLeastSquares.autoperiod()` dynamically samples frequency space $\Delta f \le \frac{1}{q \cdot T_{\text{total}}}$:
$$\chi^2(P, t_0, q) = \sum_{i} \left(\frac{y_i - \hat{y}_i(P, t_0, q)}{\sigma_i}\right)^2$$
The Signal Detection Efficiency (SDE) quantifies candidate significance:
$$\text{SDE} = \frac{\text{Power}_{\text{max}} - \text{median}(\mathbf{Power})}{\text{MAD}(\mathbf{Power}) \times 1.4826}$$

### 4.2 Harmonic Suppression
Spurious peaks at orbital harmonics ($P/2, 2P, P/3, 3P$) are identified and suppressed during iterative multi-candidate extraction.

---

## 5. Candidate Refinement & Vetting

### 5.1 Windowed Transit Least Squares (TLS)
To eliminate box-model approximation errors, candidates are refined using `transitleastsquares` (Hippke & Heller 2019) with Mandel & Agol (2002) quadratic limb darkening:
$$I(\mu) = I(0) \left[1 - u_1(1 - \mu) - u_2(1 - \mu)^2\right]$$
Executing TLS on narrow period intervals ($P_0 \pm 3\%$) over windowed cutouts reduces execution time from $>120\text{s}$ to $<1.2\text{s}$ per star.

### 5.2 Statistical False Positive Discrimination
- **Odd/Even Depth Test**: Flags eclipsing binaries whose primary and secondary depths differ ($\Delta\delta > 3\sigma$).
- **Secondary Eclipse at Phase 0.5**: Identifies occultations of non-planetary stellar companions.
- **Single-Epoch Dominance**: Rejects false triggers caused by isolated instrumental anomalies ($>75\%$ power in 1 event).
- **Quarter Recurrence**: Requires evidence across multiple observing quarters.

---

## 6. Machine Learning Candidate Ranker & Calibration

- **Model**: LightGBM gradient boosted decision trees trained on 23 physical and diagnostic features.
- **Cross-Validation**: 5-fold `GroupKFold` grouped strictly by `star_id` to guarantee zero star-level data leakage.
- **Probability Calibration**: Out-of-fold predictions are calibrated via non-parametric `IsotonicRegression` to produce well-calibrated posterior probabilities $P(\text{Transit} \mid \mathbf{x}) \in [0, 1]$.
