import numpy as np
from dataclasses import dataclass, field
from typing import Dict
from pipeline.io import RawLightCurve

@dataclass
class PreprocessedLightCurve:
    star_id: str
    time: np.ndarray
    flux: np.ndarray
    flux_err: np.ndarray
    quarter: np.ndarray
    quarter_medians: Dict[int,float] = field(default_factory=dict)
    n_points: int = 0
    time_span_days: float = 0.0
    duty_cycle: float = 0.0

def _clip(flux):
    med = np.nanmedian(flux)
    mad = np.nanmedian(np.abs(flux-med))
    scale = 1.4826*mad if mad > 0 else np.nanstd(flux)
    if not np.isfinite(scale) or scale <= 0: return np.ones(len(flux), dtype=bool)
    return (flux <= med + 5*scale) & (flux >= med - 20*scale)

def preprocess_lightcurve(raw: RawLightCurve, min_points_per_quarter: int = 50) -> PreprocessedLightCurve:
    t_out=[]; f_out=[]; e_out=[]; q_out=[]; meds={}
    quarters=np.unique(raw.quarter)
    if len(quarters)==1 and quarters[0]==0 and len(raw.time)>1:
        starts=np.r_[0, np.where(np.diff(raw.time)>10)[0]+1]; ends=np.r_[starts[1:],len(raw.time)]
        groups=[(raw.time[a:b],raw.flux[a:b],raw.flux_err[a:b],np.full(b-a,i,dtype=np.int32)) for i,(a,b) in enumerate(zip(starts,ends))]
    else:
        groups=[]
        for q in quarters:
            m=raw.quarter==q
            groups.append((raw.time[m],raw.flux[m],raw.flux_err[m],np.full(m.sum(),int(q),dtype=np.int32)))
    for t,f,e,q in groups:
        if len(t)<min_points_per_quarter: continue
        med=float(np.nanmedian(f))
        if not np.isfinite(med) or med<=0: continue
        keep=_clip(f)
        meds[int(q[0])]=med
        t_out.append(t[keep]); f_out.append(f[keep]/med); e_out.append(e[keep]/med); q_out.append(q[keep])
    if not t_out:
        med=max(float(np.nanmedian(raw.flux)),1e-8)
        return PreprocessedLightCurve(raw.star_id,raw.time,raw.flux/med,raw.flux_err/med,raw.quarter,{0:med},len(raw.time),raw.time[-1]-raw.time[0] if len(raw.time)>1 else 0,1.0)
    t=np.concatenate(t_out); f=np.concatenate(f_out); e=np.concatenate(e_out); q=np.concatenate(q_out)
    order=np.argsort(t); t=t[order]; f=f[order]; e=e[order]; q=q[order]
    span=float(t[-1]-t[0]) if len(t)>1 else 0.0
    duty=min(1.0,max(0.0,len(t)/max(1.0,span/0.0204)))
    return PreprocessedLightCurve(raw.star_id,t,f,e,q,meds,len(t),span,duty)
