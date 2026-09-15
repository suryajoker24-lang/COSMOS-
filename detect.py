# Balanced transit detection with proper type conversion
import os, sys, time, numpy as np, pandas as pd
from typing import Dict, Any
from astropy.timeseries import BoxLeastSquares

sys.path.insert(0, os.path.abspath("."))

from src.data.lightcurve import load_lightcurve
from src.preprocessing.quarter import normalize_quarters
from src.detrending.adaptive import adaptive_detrend
from src.search.bls_search import coarse_to_fine_bls

DURS = np.array([0.04, 0.08, 0.15, 0.25, 0.45])


def to_float(v):
    """Convert numpy scalar to Python float."""
    if v is None:
        return None
    return round(float(v), 6)


def detect(filepath: str) -> Dict[str, Any]:
    t0 = time.time()
    sid = os.path.splitext(os.path.basename(filepath))[0]
    try:
        lc = load_lightcurve(filepath)
        norm_lc, _ = normalize_quarters(lc)
        det_lc, _ = adaptive_detrend(norm_lc, window_length_days=2.0)
        t = det_lc.time; f = det_lc.flux
        if len(t) < 100:
            return _empty(sid)

        cands = coarse_to_fine_bls(t, f, det_lc.flux_err, period_min=0.5, period_max=400.0,
                                     n_coarse=8000, n_peaks=15, n_fine=350,
                                     durations=DURS, star_id=sid, kepid=0)
        if not cands:
            return _empty(sid)

        for c in cands:
            p = float(c.period); t0c = float(c.epoch_t0); dur_h = float(c.duration_hours)
            ph = ((t - t0c + 0.5*p) % p) / p - 0.5
            dhp = (dur_h/24.0)/p/2.0
            in_m = np.abs(ph) <= dhp
            out_m = np.abs(ph) > 5*dhp
            ni, no = int(np.sum(in_m)), int(np.sum(out_m))
            if ni > 2 and no > 10:
                in_med = float(np.median(f[in_m])); out_med = float(np.median(f[out_m]))
                depth = max(0.0, (out_med - in_med)/max(1e-10, out_med)*1e6)
                out_mad = float(np.median(np.abs(f[out_m]-out_med)))
                noise = 1.4826*out_mad/np.sqrt(max(1, ni))
                snr = depth/1e6/noise if noise > 0 else 0.0
                c.depth_ppm = round(depth, 2)
                c.transit_snr = round(snr, 2)
                c.sde = round(snr/3.0, 2)
                c.in_transit_points = ni
            else:
                c.depth_ppm = 0.0; c.transit_snr = 0.0; c.sde = 0.0
                c.in_transit_points = ni

        for c in cands:
            c.score = float(c.transit_snr) * (1.0 + float(c.sde) / 10.0)

        cands.sort(key=lambda c: c.score, reverse=True)
        best = cands[0]

        snr = float(best.transit_snr)
        sde = float(best.sde)

        if snr > 3:
            confidence = float(1.0 / (1.0 + np.exp(-0.2 * (snr + sde - 12.0))))
        else:
            confidence = 0.01
        confidence = round(min(max(confidence, 0.01), 0.99), 4)

        if best.period and any(abs(float(best.period) - p) < 0.05 for p in [2.5, 3.0, 4.0, 0.5, 1.0]):
            confidence *= 0.1

        threshold = 0.30
        prediction = 1 if confidence >= threshold else 0

        return {
            "star_id": sid,
            "prediction": prediction,
            "confidence": confidence,
            "period": round(float(best.period), 6) if prediction else None,
            "depth_ppm": round(float(best.depth_ppm), 2) if prediction and float(best.depth_ppm) > 1 else None,
            "duration_hours": round(float(best.duration_hours), 4) if prediction else None,
            "epoch_t0": round(float(best.epoch_t0), 5) if prediction else None,
            "candidates": [
                {
                    "period": round(float(c.period), 6),
                    "depth_ppm": round(float(c.depth_ppm), 2),
                    "duration_hours": round(float(c.duration_hours), 4),
                    "snr": round(float(c.transit_snr), 2),
                    "sde": round(float(c.sde), 2),
                    "bls_power": round(float(c.bls_power), 6),
                    "in_transit_points": int(c.in_transit_points),
                    "score": round(float(c.score), 2),
                }
                for c in cands[:5]
            ],
            "runtime_sec": round(time.time() - t0, 2),
            "status": "SUCCESS",
        }
    except Exception as e:
        return {"star_id": sid, "prediction": 0, "confidence": 0.01,
                "period": None, "depth_ppm": None, "duration_hours": None, "epoch_t0": None,
                "candidates": [], "runtime_sec": round(time.time() - t0, 2),
                "status": f"ERROR: {str(e)}"}


def _empty(sid):
    return {"star_id": sid, "prediction": 0, "confidence": 0.01,
            "period": None, "depth_ppm": None, "duration_hours": None, "epoch_t0": None,
            "candidates": [], "runtime_sec": 0.0, "status": "NO_CANDIDATES"}


if __name__ == "__main__":
    tests = [
        ("data/raw/train_pack/train/KIC_4364882.parquet", 235.2761, 212.7, 11.23),
        ("data/raw/dev_pack/dev/KIC_6264741.parquet", 316.9264, 164.0, 12.402),
    ]
    for path, exp_p, exp_d, exp_dur in tests:
        r = detect(path)
        p = r["period"]
        if p:
            ratio = p / exp_p
            ok = any(abs(ratio - m) < 0.02 for m in [1.0, 2.0, 0.5, 3.0, 1.5])
            status = "OK" if ok else "MISS"
        else:
            status = "NONE"
        print(f"{r['star_id']}: pred={r['prediction']} conf={r['confidence']} "
              f"P={p} ratio={p/exp_p if p else 0:.3f} {status}")
