import os
import numpy as np
import pandas as pd
from dataclasses import dataclass

@dataclass
class RawLightCurve:
    star_id: str
    time: np.ndarray
    flux: np.ndarray
    flux_err: np.ndarray
    quality: np.ndarray
    quarter: np.ndarray
    original_len: int
    retained_len: int
    removed_fraction: float
    quarters_present: list

def parse_star_id_from_path(filepath: str) -> str:
    return os.path.splitext(os.path.basename(filepath))[0]

def load_raw_lightcurve(filepath: str, strict_quality: bool = True, allowed_quality_flags: int = 0) -> RawLightCurve:
    if not os.path.exists(filepath):
        raise FileNotFoundError(filepath)
    star_id = parse_star_id_from_path(filepath)
    if filepath.lower().endswith('.parquet'):
        df = pd.read_parquet(filepath)
    elif filepath.lower().endswith('.csv'):
        df = pd.read_csv(filepath)
    else:
        raise ValueError('Supported formats are CSV and Parquet')
    df = df.rename(columns={c: c.lower().strip() for c in df.columns})
    for col in ('time', 'flux'):
        if col not in df.columns:
            raise ValueError(f"Missing required column '{col}'")
    if 'flux_err' not in df.columns:
        scale = np.nanmedian(np.abs(df['flux'].to_numpy(dtype=float)))
        df['flux_err'] = max(scale * 1e-4, 1e-8)
    if 'quality' not in df.columns:
        df['quality'] = 0
    if 'quarter' not in df.columns:
        df['quarter'] = 0
    original_len = len(df)
    time = pd.to_numeric(df['time'], errors='coerce').to_numpy(float)
    flux = pd.to_numeric(df['flux'], errors='coerce').to_numpy(float)
    ferr = pd.to_numeric(df['flux_err'], errors='coerce').to_numpy(float)
    quality = pd.to_numeric(df['quality'], errors='coerce').fillna(0).to_numpy(np.int64) if hasattr(pd.to_numeric(df['quality'], errors='coerce'), 'fillna') else np.zeros(len(df), dtype=np.int64)
    quarter = pd.to_numeric(df['quarter'], errors='coerce').fillna(0).to_numpy(np.int64) if hasattr(pd.to_numeric(df['quarter'], errors='coerce'), 'fillna') else np.zeros(len(df), dtype=np.int64)
    valid = np.isfinite(time) & np.isfinite(flux) & (flux > 0) & np.isfinite(ferr) & (ferr >= 0)
    if strict_quality:
        valid &= (quality == 0) if allowed_quality_flags == 0 else ((quality & ~allowed_quality_flags) == 0)
    if valid.sum() < 100:
        valid = np.isfinite(time) & np.isfinite(flux) & (flux > 0) & np.isfinite(ferr)
    dfc = pd.DataFrame({'time':time[valid], 'flux':flux[valid], 'flux_err':ferr[valid], 'quality':quality[valid], 'quarter':quarter[valid]})
    dfc = dfc.sort_values('time').drop_duplicates('time')
    n = len(dfc)
    return RawLightCurve(star_id, dfc.time.to_numpy(float), dfc.flux.to_numpy(float), dfc.flux_err.to_numpy(float), dfc.quality.to_numpy(np.int32), dfc.quarter.to_numpy(np.int32), original_len, n, (original_len-n)/max(1,original_len), sorted(dfc.quarter.unique().tolist()))
