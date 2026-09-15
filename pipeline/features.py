import numpy as np
import pandas as pd
from pipeline.models import TransitCandidate
from pipeline.detrend import DetrendedLightCurve
from pipeline.preprocess import PreprocessedLightCurve

FEATURE_NAMES=['period','log_period','duration_hours','depth_ppm','log_depth','sde','snr','fap','rp_rs','duration_over_period','odd_even_mismatch','secondary_eclipse_score','n_transits','n_quarters','single_epoch_fraction','systematic_period_flag','cdpp_ppm','duty_cycle','time_span_days','depth_to_cdpp_ratio','transit_duty_cycle','log_snr','source_method_is_tls']

def extract_candidate_features(cand,detrended,preprocessed=None):
    p=max(.001,cand.period); depth=max(1,cand.depth_ppm); snr=max(.01,cand.snr); span=max(1,float(detrended.time[-1]-detrended.time[0]))
    duty=preprocessed.duty_cycle if preprocessed is not None else .9; cdpp=max(1,detrended.cdpp_ppm); dur=max(.01,cand.duration)
    return {'period':p,'log_period':np.log10(p),'duration_hours':dur,'depth_ppm':depth,'log_depth':np.log10(depth),'sde':cand.sde,'snr':snr,'fap':cand.fap,'rp_rs':cand.rp_rs,'duration_over_period':(dur/24)/p,'odd_even_mismatch':cand.odd_even_mismatch,'secondary_eclipse_score':cand.secondary_eclipse_score,'n_transits':cand.n_transits,'n_quarters':cand.n_quarters,'single_epoch_fraction':cand.single_epoch_fraction,'systematic_period_flag':float(cand.systematic_period_flag),'cdpp_ppm':cdpp,'duty_cycle':duty,'time_span_days':span,'depth_to_cdpp_ratio':depth/cdpp,'transit_duty_cycle':cand.n_transits*(dur/24)/span,'log_snr':np.log10(snr),'source_method_is_tls':float('TLS' in cand.source_method)}

def features_dict_to_dataframe(items):
    df=pd.DataFrame(items)
    for c in FEATURE_NAMES:
        if c not in df:df[c]=0.0
    return df[FEATURE_NAMES]
