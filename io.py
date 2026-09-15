# Robust Scientific Light Curve Ingestion & Quality Validation
import os
import re
import numpy as np
import pandas as pd
from typing import Dict, Any, Tuple, Optional
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
    """Extracts standardized star_id (e.g. STAR_0001 or KIC_5306984) from filename."""
    base = os.path.basename(filepath)
    name = os.path.splitext(base)[0]
    return name

def load_raw_lightcurve(
    filepath: str,
    strict_quality: bool = True,
    allowed_quality_flags: int = 0
) -> RawLightCurve:
    """
    Loads raw Kepler SAP light curve from Parquet or CSV.
    Performs finite validation, quality bitmask filtering, and monotonic sorting.
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Light curve file not found: {filepath}")
        
    star_id = parse_star_id_from_path(filepath)
    
    if filepath.endswith(".parquet"):
        df = pd.read_parquet(filepath)
    else:
        df = pd.read_csv(filepath)
        
    # Standardize column names
    col_map = {c: c.lower().strip() for c in df.columns}
    df = df.rename(columns=col_map)
    
    required_cols = ["time", "flux"]
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"Missing required column '{col}' in {filepath}")
            
    # Fallbacks for optional columns
    if "flux_err" not in df.columns:
        df["flux_err"] = np.ones(len(df), dtype=np.float64) * np.nanmedian(df["flux"]) * 1e-4
    if "quality" not in df.columns:
        df["quality"] = np.zeros(len(df), dtype=np.int32)
    if "quarter" not in df.columns:
        df["quarter"] = np.zeros(len(df), dtype=np.int32)
        
    original_len = len(df)
    
    # 1. Finite and positive flux mask
    valid_mask = (
        np.isfinite(df["time"].values) &
        np.isfinite(df["flux"].values) &
        (df["flux"].values > 0) &
        np.isfinite(df["flux_err"].values)
    )
    
    # 2. Quality mask
    if strict_quality:
        if allowed_quality_flags == 0:
            valid_mask &= (df["quality"].values == 0)
        else:
            valid_mask &= ((df["quality"].values & ~allowed_quality_flags) == 0)
            
    df_clean = df[valid_mask].copy()
    
    if len(df_clean) < 100:
        # Fallback if quality filtering removes too much data
        valid_mask = (
            np.isfinite(df["time"].values) &
            np.isfinite(df["flux"].values) &
            (df["flux"].values > 0)
        )
        df_clean = df[valid_mask].copy()
        
    # 3. Monotonic sorting & deduplication
    df_clean = df_clean.sort_values("time").drop_duplicates(subset=["time"])
    
    retained_len = len(df_clean)
    removed_fraction = round((original_len - retained_len) / max(1, original_len), 4)
    quarters = sorted(df_clean["quarter"].unique().tolist())
    
    return RawLightCurve(
        star_id=star_id,
        time=df_clean["time"].values.astype(np.float64),
        flux=df_clean["flux"].values.astype(np.float64),
        flux_err=df_clean["flux_err"].values.astype(np.float64),
        quality=df_clean["quality"].values.astype(np.int32),
        quarter=df_clean["quarter"].values.astype(np.int32),
        original_len=original_len,
        retained_len=retained_len,
        removed_fraction=removed_fraction,
        quarters_present=quarters
    )

