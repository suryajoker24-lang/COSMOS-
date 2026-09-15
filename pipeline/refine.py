import warnings
try:
    from transitleastsquares import transitleastsquares
    HAS_TLS=True
except ImportError:
    HAS_TLS=False

def refine_candidate_tls(detrended,cand,period_window_pct=0.02):
    if not HAS_TLS or cand.period<=0 or len(detrended.time)<30:return cand
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            res=transitleastsquares(detrended.time,detrended.flux,detrended.flux_err).power(period_min=max(.2,cand.period*(1-period_window_pct)),period_max=cand.period*(1+period_window_pct),oversampling_factor=2,duration_grid_step=1.2,show_progress_bar=False,verbose=False,use_threads=4)
        if getattr(res,'SDE',0)>1 and getattr(res,'period',0)>0:
            cand.source_method='TLS_refined'; cand.period=float(res.period); cand.t0=float(res.T0); cand.duration=float(res.duration*24); cand.depth_ppm=float(res.depth*1e6); cand.sde=float(res.SDE); cand.snr=float(res.snr); cand.rp_rs=float(res.rp_rs); cand.fap=float(res.FAP); cand.n_transits=int(res.distinct_transit_count); cand.folded_phase=getattr(res,'folded_phase',None); cand.folded_flux=getattr(res,'folded_y',None); cand.tls_model=getattr(res,'model_folded_model',None)
    except Exception: pass
    return cand
