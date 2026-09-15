# NASA & MAST Cross-Validation Engine — Technical Report & Verification Audit

## 1. Executive Summary

This report documents the implementation and verification of the **NASA Exoplanet Archive and STScI MAST Cross-Validation Engine** within the COSMOS Exoplanet Research Workstation.

The engine establishes an automated, zero-hallucination cross-referencing workflow that queries official, authoritative astronomical archives to validate local detection signals, identify period harmonic aliases, flag conflicting false-positive signatures, and inspect available satellite observations.

---

## 2. Multi-Table NASA & MAST Query Architecture

The engine queries live IPAC Caltech and STScI services via `astroquery` and `lightkurve`, falling back to persistent cache storage (`data/nasa_cache/` and the SQLite `nasa_validations` table) for sub-millisecond warm lookups.

### Authoritative Tables Queried
1. **Planetary Systems Table (`ps` / `pscomppars`)**:
   - Primary source for peer-reviewed confirmed exoplanets (`pl_name`, `pl_orbper`, `pl_trandep`, `pl_trandur`, `pl_tranmid`).
2. **Kepler Cumulative Object of Interest Table (`cumulative` / `q1_q17_dr25_koi`)**:
   - Official KOI catalog (`kepoi_name`, `koi_disposition`, `koi_period`, `koi_depth`, `koi_duration`, `koi_time0bk`).
3. **Kepler Threshold Crossing Event Table (`q1_q17_dr25_tce`)**:
   - Raw algorithmic detection events (`tce_plnt_num`, `tce_period`, `tce_depth`, `tce_duration`, `tce_time0bk`).
4. **Kepler Stellar Characteristics Table (`keplerstellar`)**:
   - Host star astrophysical properties ($T_{\text{eff}}$, $\log g$, Stellar Radius $R_\star$, Metallicity $[\text{Fe/H}]$).
5. **STScI MAST Observation Cross-Check**:
   - Validates whether raw calibrated spacecraft photometric data actually exists for the target across all 17 Kepler operational quarters (`Kepler Quarter 00` through `17`).

---

## 3. Deterministic Decision Matrix

Every candidate evaluated against NASA archives is classified into exactly one of three deterministic statuses:

```
                  ┌────────────────────────────────────────────────────────┐
                  │ Target Star Input (e.g. KIC_11904011, STAR_0037, etc.) │
                  └──────────────────────────┬─────────────────────────────┘
                                             │
                                    Resolve Canonical KIC
                                             │
                        ┌────────────────────┴────────────────────┐
                        ▼                                         ▼
                 Authoritative KIC                       Anonymized / Synthetic
                        │                                         │
             Query NASA (PS/KOI/TCE/MAST)                         │
                        │                                         │
             ┌──────────┴──────────┐                              │
             ▼                     ▼                              │
       Records Found       No Records in NASA                     │
             │                     │                              │
     Match Candidates              │                              │
             │                     │                              │
     ┌───────┴───────┐             │                              │
     ▼               ▼             ▼                              ▼
Match / Harmonic  Conflict   UNVERIFIED                      UNVERIFIED
(Period ±2%)     (Divergent) (Never Conflict!)              (Zero Hallucination)
     │               │             │                              │
     ▼               ▼             ▼                              ▼
NASA VERIFIED  NASA CONFLICT   UNVERIFIED                     UNVERIFIED
```

### Tolerance Thresholds
| Parameter | Tolerance | Notes |
| :--- | :--- | :--- |
| **Direct Period Match** | $\pm 2.0\%$ | Agreement $\ge 98\%$ against gold-standard orbital period |
| **Harmonic Multiples** | $\pm 2.0\%$ | Check resonances: $1/2\times, 2\times, 1/3\times, 3\times, 1/4\times, 4\times$ |
| **Transit Depth** | $\le 30.0\%$ | Comparison against cataloged ppm depth |
| **Transit Duration** | $\le 30.0\%$ | Comparison against cataloged transit duration hours |
| **Phase / Epoch** | $\le 0.05$ phase | Transit center time alignment $\Delta\phi \le 0.05$ |

### Strict Rule on Missing Data
> **Invariant**: When a target has no corresponding KOI, TCE, or Planetary record in the NASA archive (e.g., `KIC 11904011`), the system **MUST** output `UNVERIFIED`. The system will **NEVER** mark a target as `NASA CONFLICT` merely due to the absence of an archival record.

---

## 4. Frontend User Interface Implementation

### 1. Critical Warning State on False Positives (`#ef4444`)
- When `classificationVerdict === "False Positive"` or `isFalsePositive === true`:
  - Banner card (`#verdictCard`) switches to critical warning state hex `#ef4444` (`border-color: #ef4444; background: rgba(239, 68, 68, 0.08); box-shadow: 0 0 20px rgba(239, 68, 68, 0.25)`).
  - Verdict text displays `FALSE POSITIVE` in `#ef4444`.

### 2. Physics-Vetting Diagnostic Deck (`#systemNotesDeck`)
- Located directly in the summary deck / CARL quick explanations area.
- Exposes `systemNotes` to explain the exact physical mechanism responsible for candidate rejection:
  - *Eclipsing Binary Signature (Odd/Even depth mismatch detected)*
  - *Stellar Harmonic Artifact (Alias Loop Triggered)*
  - *Eclipsing Binary Signature (Stellar Eclipse Depth > 5%)*
  - *Low Confidence Threshold*

### 3. Light Curve Telemetry (`plotData.x` & `plotData.y`)
- Connected directly to `plotData.x` (Time in BKJD Days) and `plotData.y` (Detrended Relative Flux).
- Phase-folded profile viewer automatically bins and overlays transits according to detected or archival periods.

### 4. NASA Cross-Validation Card (`#nasaCrossValidationSection`)
- **Status Badges**:
  - `[NASA VERIFIED]` — Emerald `#10b981`
  - `[NASA CONFLICT]` — Red `#ef4444`
  - `[UNVERIFIED]` — Slate `#64748b`
- **Telemetry Comparison Table**: Side-by-side display of Orbital Period, Depth, Duration, and Epoch with calculated percentage deviation and status tags (`MATCH`, `HARMONIC`, `CONFLICT`, `UNVERIFIED`).
- **MAST Availability Chip**: Real-time counter of available Kepler quarters/products.
- **Clickable Source Links**: Direct URLs to NASA Exoplanet Archive, KOI Table, TCE Table, and STScI MAST portal.
- **Refresh Action**: Interactive `[Refresh NASA]` button that bypasses local caches to query live upstream servers on demand.

---

## 5. Automated Test Suite Verification

The engine is verified by `tests/test_nasa_validation.py` using `pytest`:

```
============================= test session starts =============================
platform win32 -- Python 3.13.5, pytest-9.1.1, pluggy-1.6.0
rootdir: C:\Users\surya\Downloads\COSMOS

tests/test_nasa_validation.py::test_resolve_canonical_kic PASSED         [ 14%]
tests/test_nasa_validation.py::test_match_direct_hit PASSED              [ 28%]
tests/test_nasa_validation.py::test_match_harmonic_alias PASSED          [ 42%]
tests/test_nasa_validation.py::test_match_conflict_divergent_period PASSED [ 57%]
tests/test_nasa_validation.py::test_synthetic_star_unverified PASSED     [ 71%]
tests/test_nasa_validation.py::test_unverified_when_nasa_records_absent PASSED [ 85%]
tests/test_nasa_validation.py::test_kic_11904011_live_archival_status PASSED [100%]

======================== 7 passed, 1 warning in 40.23s ========================
```

### Benchmark Star Verification Results:
- **`KIC 11904011`**:
  - MAST Status: **15 Kepler Quarters Available** (`Q00`, `Q01`, `Q02`, `Q03`, `Q04`, `Q05`, `Q06`, `Q07`, `Q09`, `Q10`, `Q11`, `Q13`, `Q14`, `Q15`, `Q17`).
  - NASA Catalog: 0 KOIs, 0 TCEs.
  - Verdict: **`UNVERIFIED`** (Verified compliant with Section 11 Case C).
- **`STAR_0037`**:
  - Anonymized challenge target.
  - Verdict: **`UNVERIFIED`** (Zero hallucination; prevents false matching against synthetic IDs).
- **`KIC 5306984`**:
  - Gold-standard period: 140.32 days.
  - 2x harmonic alias input (280.64d): Classified as **`NASA VERIFIED (2x harmonic)`**.
  - Divergent period (42.15d): Classified as **`NASA CONFLICT`**.
