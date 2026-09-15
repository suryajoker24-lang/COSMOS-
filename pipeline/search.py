import numpy as np
from astropy.timeseries import BoxLeastSquares
from pipeline.detrend import DetrendedLightCurve
from pipeline.models import TransitCandidate

DURATIONS_DAYS=np.array([0.02,0.04,0.08,0.15,0.25,0.45,0.70])

def search_candidates_bls(detrended: DetrendedLightCurve, min_period=0.5, max_period=None, top_k=5, sde_threshold=5.0, n_coarse=10000, n_fine=500, fine_window_pct=0.03, **kwargs):
    t,f,err=detrended.time,detrended.flux,detrended.flux_err
    if len(t)<100:return []
    baseline=float(t[-1]-t[0])
    max_period=min(400.0,baseline/2.0) if max_period is None else min(400.0,max_period,baseline/2.0)
    if max_period<=min_period:return []
    durations=DURATIONS_DAYS[(DURATIONS_DAYS>=0.02)&(DURATIONS_DAYS<=min(0.8,max_period*0.2))]
    if len(durations)==0: durations=np.array([0.04])
    bls=BoxLeastSquares(t,f,dy=np.clip(err,1e-10,None))
    # Uniform frequency spacing gives the period resolution required at long P.
    freqs=np.linspace(1/max_period,1/min_period,n_coarse)
    periods=1/freqs[::-1]
    try:r=bls.power(periods,durations)
    except Exception:return []
    power=np.asarray(r.power); med=np.nanmedian(power); mad=np.nanmedian(np.abs(power-med)); scale=max(1e-12,1.4826*mad)
    order=np.argsort(power)[::-1]; peaks=[]
    for i in order:
        if not np.isfinite(power[i]):continue
        p=periods[i]
        if any(abs(p/x-1)<0.05 for x in peaks):continue
        peaks.append(float(p))
        if len(peaks)>=top_k*3:break
    out=[]
    for p0 in peaks:
        fp=np.linspace(max(min_period,p0*(1-fine_window_pct)),min(max_period,p0*(1+fine_window_pct)),n_fine)
        try:fr=bls.power(fp,durations)
        except Exception:continue
        j=int(np.nanargmax(fr.power)); p=float(fr.period[j]); pw=float(fr.power[j]); fmed=np.nanmedian(fr.power); fmad=np.nanmedian(np.abs(fr.power-fmed)); sde=(pw-fmed)/max(1e-12,1.4826*fmad)
        if sde<sde_threshold:continue
        t0=float(fr.transit_time[j]); dur=float(fr.duration[j]); depth=max(0.0,float(fr.depth[j])); phase=((t-t0+0.5*p)%p)/p-0.5; in_tr=np.abs(phase)<dur/(2*p)
        n_in=int(in_tr.sum()); n_epochs=len(np.unique(np.round((t[in_tr]-t0)/p))) if n_in else 0
        out_mask=~in_tr; mad_out=np.nanmedian(np.abs(f[out_mask]-np.nanmedian(f[out_mask]))) if out_mask.any() else np.nan
        noise=1.4826*mad_out if np.isfinite(mad_out) and mad_out>0 else np.nanstd(f[out_mask])
        snr=depth*np.sqrt(max(1,n_in))/max(noise,1e-8)
        sysflag=any(abs(p-x)/max(x,1e-8)<0.02 for x in (1.0,2.5,3.0,4.0))
        c=TransitCandidate(star_id=detrended.star_id,candidate_id=len(out)+1,source_method='BLS_coarse2fine',period=p,t0=t0,duration=dur*24,depth_ppm=depth*1e6,sde=sde,snr=snr,fap=float(np.exp(-sde/2)),rp_rs=np.sqrt(depth),n_transits=n_epochs,single_epoch_fraction=1.0 if n_epochs<=1 else 1.0/n_epochs,systematic_period_flag=sysflag,detrending_method=detrended.method,detrending_window=detrended.window_length,folded_phase=phase,folded_flux=f)
        out.append(c)
        if len(out)>=top_k:break
    return out
