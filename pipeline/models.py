import numpy as np
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional

@dataclass
class TransitCandidate:
    star_id: str
    candidate_id: int = 1
    source_method: str = 'BLS'
    period: float = 0.0
    t0: float = 0.0
    duration: float = 0.0
    depth_ppm: float = 0.0
    sde: float = 0.0
    snr: float = 0.0
    fap: float = 1.0
    rp_rs: float = 0.0
    odd_even_mismatch: float = 0.0
    secondary_eclipse_score: float = 0.0
    n_transits: int = 0
    n_quarters: int = 0
    single_epoch_fraction: float = 0.0
    systematic_period_flag: bool = False
    detrending_method: str = 'wotan_biweight'
    detrending_window: float = 0.75
    vetting_flags: Dict[str, Any] = field(default_factory=dict)
    ranking_score: float = 0.0
    confidence: float = 0.0
    folded_phase: Optional[Any] = None
    folded_flux: Optional[Any] = None
    tls_model: Optional[Any] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        for key in ('folded_phase', 'folded_flux', 'tls_model'):
            value = d.get(key)
            if isinstance(value, np.ndarray):
                d[key] = value.tolist()
        return d

@dataclass
class StarDetectionResult:
    star_id: str
    prediction: int = 0
    confidence: float = 0.0
    period: Optional[float] = None
    depth_ppm: Optional[float] = None
    duration_hours: Optional[float] = None
    best_candidate: Optional[TransitCandidate] = None
    all_candidates: List[TransitCandidate] = field(default_factory=list)
    status: str = 'SUCCESS'
    error_message: Optional[str] = None
    runtime_sec: float = 0.0
    cadence_count: int = 0
    retained_cadence_count: int = 0
    provenance: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'star_id': self.star_id,
            'prediction': int(self.prediction),
            'confidence': round(float(self.confidence), 4),
            'period': round(float(self.period), 6) if self.period is not None else None,
            'depth_ppm': round(float(self.depth_ppm), 2) if self.depth_ppm is not None else None,
            'duration_hours': round(float(self.duration_hours), 4) if self.duration_hours is not None else None,
            'status': self.status,
            'runtime_sec': round(float(self.runtime_sec), 2),
            'candidate_count': len(self.all_candidates),
            'best_candidate': self.best_candidate.to_dict() if self.best_candidate else None,
            'provenance': self.provenance,
        }
