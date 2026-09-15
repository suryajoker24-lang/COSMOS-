import numpy as np

def gp_detrend_lightcurve(lc, transit_mask=None, rho=5.0, sigma=0.001):
    """Optional celerite2 path; falls back to Wotan/median detrending when unavailable."""
    try:
        import celerite2
        from celerite2 import terms
        from pipeline.detrend import DetrendedLightCurve, estimate_cdpp_6hr
        fit=~transit_mask if transit_mask is not None else np.ones(len(lc.time),dtype=bool)
        t0=lc.time[0]; tf=lc.time-t0; y=lc.flux-1; err=np.clip(lc.flux_err,1e-6,.1)
        w0=2*np.pi/max(.5,rho); kernel=terms.SHOTerm(S0=sigma**2/(w0/np.sqrt(2)),w0=w0,Q=1/np.sqrt(2)); gp=celerite2.GaussianProcess(kernel,mean=0); gp.compute(tf[fit],yerr=err[fit]); trend=gp.predict(y[fit],t=tf)+1
        flat=lc.flux/np.clip(trend,1e-4,None)
        return DetrendedLightCurve(lc.star_id,lc.time,flat,trend,lc.flux_err,'celerite2_gp_sho',rho,round(estimate_cdpp_6hr(flat),2))
    except Exception:
        from pipeline.detrend import detrend_lightcurve
        return detrend_lightcurve(lc,method='biweight',window_length=.75,mask=transit_mask)
