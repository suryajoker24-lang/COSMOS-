# Scientific Period Search using Astropy BoxLeastSquares (Kovács et al. 2002)
# Coarse-to-fine approach: search wide grid, then refine around peaks
import numpy as np
import pandas as pd
from typing import List, Dict, Any, Optional, Tuple
from astropy.timeseries import BoxLeastSquares
from pipeline.detrend import DetrendedLightCurve
from pipeline.models import TransitCandidate

DEFAULT_DURATIONS = np.array([0.04, 0.08, 0.15, 0.25, 0.45, 0.70])  # days


def search_candidates_bls(
    detrended: DetrendedLightCurve,
    min_period: float = 0.5,
    max_period: Optional[float] = None,
    min_duration_hours: float = 0.5,
    max_duration_hours: float = 12.0,
    top_k: int = 5,
    sde_threshold: float = 5.0,
    n_coarse: int = 10000,
    n_fine: int = 500,
    fine_window_pct: float = 0.03,
) -> List[TransitCandidate]:
    """
    Coarse-to-fine BLS period search.

    Phase 1: Coarse grid search across full period range with uniform frequency spacing.
    Phase 2: Fine refinement (±3%) around each top peak.

    Extended to handle periods up to 400 days as per problem statement.
    The coarse-to-fine approach keeps computation tractable.
    """
    time = detrended.time
    flux = detrended.flux
    flux_err = detrended.flux_err
    star_id = detrended.star_id

    if len(time) < 50:
        return []

    time_span = float(time[-1] - time[0])
    if max_period is None or max_period > time_span / 2.0:
        max_period = min(time_span / 2.0, 400.0)

    if min_period >= max_period:
        return []

    # Duration grid in days
    dur_max = min(max_duration_hours / 24.0, min_period * 0.8)
    dur_min = max(0.01, min(min_duration_hours / 24.0, dur_max * 0.5))
    durations = np.linspace(dur_min, dur_max, 8)

    bls = BoxLeastSquares(time, flux, dy=flux_err)

    # ========== PHASE 1: COARSE GRID ==========
    f_min = 1.0 / max_period
    f_max = 1.0 / min_period
    freqs = np.linspace(f_min, f_max, n_coarse)
    coarse_periods = 1.0 / freqs[::-1]

    try:
        coarse_res = bls.power(coarse_periods, durations)
        coarse_power = np.asarray(coarse_res.power)
    except Exception as e:
        print(f"BLS coarse search exception: {e}")
        return []

    if len(coarse_power) == 0 or np.all(np.isnan(coarse_power)):
        return []

    # ========== PEAK EXTRACTION with NMS ==========
    sorted_idx = np.argsort(coarse_power)[::-1]
    peak_indices = []
    suppressed = np.zeros(len(coarse_periods), dtype=bool)

    for idx in sorted_idx:
        if suppressed[idx] or not np.isfinite(coarse_power[idx]):
            continue
        peak_indices.append(idx)
        # Suppress ±5% period neighborhood
        p_val = coarse_periods[idx]
        lo = np.searchsorted(coarse_periods, p_val * 0.95)
        hi = np.searchsorted(coarse_periods, p_val * 1.05)
        suppressed[lo:hi] = True
        if len(peak_indices) >= top_k * 3:  # Get more peaks than needed for safety
            break

    # ========== PHASE 2: FINE REFINEMENT ==========
    candidates: List[TransitCandidate] = []
    seen_periods = []

    for peak_idx in peak_indices[:top_k * 3]:
        p0 = coarse_periods[peak_idx]
        coarse_sde = float((coarse_power[peak_idx] - np.nanmedian(coarse_power)) /
                           max(1e-9, 1.4826 * np.nanmedian(np.abs(coarse_power - np.nanmedian(coarse_power)))))

        if coarse_sde < sde_threshold * 0.5:
            continue

        # Fine grid around peak
        width = fine_window_pct * p0
        fine_p = np.linspace(max(min_period, p0 - width), p0 + width, n_fine)
        fine_p = fine_p[fine_p >= min_period]
        if len(fine_p) < 10:
            continue

        try:
            fine_res = bls.power(fine_p, durations)
            fine_power = np.asarray(fine_res.power)
        except Exception:
            continue

        if len(fine_power) == 0 or np.all(np.isnan(fine_power)):
            continue

        best_j = int(np.nanargmax(fine_power))
        best_power = float(fine_power[best_j])
        best_period = float(fine_res.period[best_j])
        best_t0 = float(fine_res.transit_time[best_j])
        best_duration_days = float(fine_res.duration[best_j])
        best_depth = float(fine_res.depth[best_j])

        # SDE on fine grid
        fine_med = np.nanmedian(fine_power)
        fine_mad = np.nanmedian(np.abs(fine_power - fine_med))
        fine_sde = float((best_power - fine_med) / max(1e-9, 1.4826 * fine_mad))

        if fine_sde < sde_threshold:
            continue

        # Check for period aliasing with already accepted candidates
        is_alias = False
        for sp in seen_periods:
            ratio = best_period / sp
            if any(abs(ratio - m) < 0.02 for m in [0.5, 1.0, 2.0, 3.0, 0.333, 0.25, 1.5, 2.5]):
                is_alias = True
                break
        if is_alias:
            continue

        seen_periods.append(best_period)

        # Phase folding & transit characterization
        phase = ((time - best_t0 + 0.5 * best_period) % best_period) / best_period - 0.5
        dur_half = best_duration_days / 2.0
        in_transit = np.abs(phase) * best_period < dur_half * best_period
        # Actually more precise: |phase| * period < dur/2
        in_transit = np.abs(phase) < (best_duration_days / best_period / 2.0)
        n_in = np.sum(in_transit)

        # SNR calculation
        out_transit = ~in_transit
        if np.sum(out_transit) > 0:
            out_mad = np.nanmedian(np.abs(flux[out_transit] - np.nanmedian(flux[out_transit])))
            noise = 1.4826 * out_mad if out_mad > 0 else np.nanstd(flux[out_transit])
            snr = float((best_depth * np.sqrt(max(1, n_in))) / max(noise, 1e-6))
        else:
            snr = 0.0

        # Radius ratio
        rp_rs = float(np.sqrt(max(0.0, best_depth)))

        # Count distinct transits
        transit_epochs = np.round((time[in_transit] - best_t0) / best_period)
        n_transits = len(np.unique(transit_epochs)) if len(transit_epochs) > 0 else 0

        # Single epoch dominance
        if n_transits > 0 and len(transit_epochs) > 0:
            epoch_counts = pd.Series(transit_epochs).value_counts()
            single_epoch_frac = float(epoch_counts.max() / len(transit_epochs))
        else:
            single_epoch_frac = 1.0

        # Systematic period check
        is_systematic = any(abs(best_period - p_sys) < 0.02 for p_sys in [2.5, 3.0, 4.0, 0.5, 1.0])

        # FAP approximation
        fap = float(np.exp(-fine_sde / 2.0))

        candidate = TransitCandidate(
            star_id=star_id,
            candidate_id=len(candidates) + 1,
            source_method="BLS_coarse2fine",
            period=round(best_period, 6),
            t0=round(best_t0, 5),
            duration=round(best_duration_days * 24.0, 4),
            depth_ppm=round(max(0.0, best_depth * 1e6), 2),
            sde=round(fine_sde, 3),
            snr=round(snr, 2),
            fap=round(fap, 6),
            rp_rs=round(rp_rs, 4),
            n_transits=int(n_transits),
            single_epoch_fraction=round(single_epoch_frac, 3),
            systematic_period_flag=is_systematic,
            detrending_method=detrended.method,
            detrending_window=detrended.window_length,
            folded_phase=phase,
            folded_flux=flux,
        )
        candidates.append(candidate)

        if len(candidates) >= top_k:
            break

    return candidates
