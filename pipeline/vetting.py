import numpy as np
import pandas as pd
from pipeline.models import TransitCandidate
from pipeline.detrend import DetrendedLightCurve

def vet_candidate(detrended: DetrendedLightCurve,cand: TransitCandidate,quarter_array=None):
    t,f=detrended.time,detrended.flux; p=cand.period; dur=max(0.01,cand.duration/24)
    if p<=0:return cand
    phase=((t-cand.t0+0.5*p)%p)/p-0.5; primary=np.abs(phase*p)<=dur/2; epochs=np.round((t-cand.t0)/p)
    odd=primary&(np.abs(epochs)%2==1); even=primary&(np.abs(epochs)%2==0)
    od=1-np.nanmedian(f[odd]) if odd.sum()>=2 else cand.depth_ppm*1e-6; ed=1-np.nanmedian(f[even]) if even.sum()>=2 else cand.depth_ppm*1e-6
    se=np.sqrt((np.nanstd(f[odd])/np.sqrt(max(1,odd.sum())))**2+(np.nanstd(f[even])/np.sqrt(max(1,even.sum())))**2)
    cand.odd_even_mismatch=float(abs(od-ed)/max(1e-5,se))
    secondary=np.abs(np.abs(phase)-0.5)*p<=dur/2
    sd=max(0.0,1-np.nanmedian(f[secondary])) if secondary.sum()>=2 else 0.0
    ss=np.nanstd(f[secondary])/np.sqrt(max(1,secondary.sum())) if secondary.sum()>=2 else 1e-4
    cand.secondary_eclipse_score=float(sd/max(1e-5,ss))
    cand.n_transits=len(np.unique(epochs[primary])) if primary.any() else cand.n_transits
    if quarter_array is not None and len(quarter_array)==len(t):cand.n_quarters=len(np.unique(quarter_array[primary]))
    if primary.any():
        counts=pd.Series(epochs[primary]).value_counts(); cand.single_epoch_fraction=float(counts.max()/len(epochs[primary]))
    cand.vetting_flags={'pass_odd_even':cand.odd_even_mismatch<3.5,'pass_secondary':cand.secondary_eclipse_score<3.0,'pass_multi_transit':cand.n_transits>=2,'pass_epoch_fraction':cand.single_epoch_fraction<0.75,'pass_systematic':not cand.systematic_period_flag,'pass_duration':0.5<=cand.duration<=20}
    return cand
