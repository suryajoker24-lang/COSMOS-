import os, time, numpy as np
import pandas as pd
import joblib
from pipeline.io import load_raw_lightcurve
from pipeline.preprocess import preprocess_lightcurve
from pipeline.detrend import detrend_lightcurve
from pipeline.search import search_candidates_bls
from pipeline.refine import refine_candidate_tls
from pipeline.vetting import vet_candidate
from pipeline.features import extract_candidate_features, features_dict_to_dataframe
from pipeline.models import StarDetectionResult

class ExoHunterModel:
    """Candidate ranker. Raw model probability is used for ranking by default; an old isotonic artifact is never trusted silently."""
    def __init__(self, model_path='models/candidate_ranker.joblib', threshold=0.5, use_calibrator=False):
        self.ranker=None; self.calibrator=None; self.threshold=threshold; self.use_calibrator=use_calibrator
        if model_path and os.path.exists(model_path): self.load(model_path)
    def load(self,path):
        data=joblib.load(path)
        if isinstance(data,dict): self.ranker=data.get('ranker') or data.get('model'); self.calibrator=data.get('calibrator'); self.threshold=float(data.get('threshold',self.threshold))
        else: self.ranker=data
    def predict_candidate_proba(self,df):
        if self.ranker is None:
            sde=df.get('sde',pd.Series(0,index=df.index)).to_numpy(float); snr=df.get('snr',pd.Series(0,index=df.index)).to_numpy(float)
            odd=df.get('odd_even_mismatch',pd.Series(0,index=df.index)).to_numpy(float); sec=df.get('secondary_eclipse_score',pd.Series(0,index=df.index)).to_numpy(float)
            p=1/(1+np.exp(-.65*(sde-6)))
            p*=np.clip(1-.12*np.maximum(0,odd-2),.2,1); p*=np.clip(1-.12*np.maximum(0,sec-1.5),.2,1); p=np.maximum(p,1/(1+np.exp(-.25*(snr-6)))*.5)
            return np.clip(p,.001,.999)
        try:
            p=self.ranker.predict_proba(df)[:,1]
            if self.use_calibrator and self.calibrator is not None: p=self.calibrator.predict(p)
            return np.clip(np.asarray(p,float),.001,.999)
        except Exception:
            return ExoHunterModel(model_path=None).predict_candidate_proba(df)

def _transit_mask(time,c):
    p=float(c.period); dur=max(.01,float(c.duration)/24); phase=((time-float(c.t0)+.5*p)%p)/p-.5
    return np.abs(phase)<dur/(2*p)

def process_star_end_to_end(filepath, model=None, use_gp=False, use_tls=True, detrend_window=.75):
    start=time.perf_counter(); raw=load_raw_lightcurve(filepath); pre=preprocess_lightcurve(raw)
    det=detrend_lightcurve(pre,window_length=detrend_window)
    candidates=search_candidates_bls(det,min_period=.5,max_period=None,top_k=7)
    # Transit-masked second pass: prevents the first trend fit from absorbing a real dip.
    if candidates:
        mask=_transit_mask(det.time,candidates[0])
        det2=detrend_lightcurve(pre,window_length=detrend_window,mask=mask)
        candidates2=search_candidates_bls(det2,min_period=.5,max_period=None,top_k=7)
        if candidates2: det=det2; candidates=candidates2
    if not candidates:
        return StarDetectionResult(raw.star_id,0,.001,status='SUCCESS',runtime_sec=time.perf_counter()-start,cadence_count=raw.original_len,retained_cadence_count=raw.retained_len,provenance={'detrending':det.method,'window_days':det.window_length,'cdpp_ppm':det.cdpp_ppm,'n_candidates':0})
    refined=[]; feats=[]
    for c in candidates:
        if use_tls:c=refine_candidate_tls(det,c)
        c=vet_candidate(det,c,pre.quarter); refined.append(c); feats.append(extract_candidate_features(c,det,pre))
    probs=(model or ExoHunterModel(model_path=None)).predict_candidate_proba(features_dict_to_dataframe(feats))
    for c,p in zip(refined,probs):
        vet_penalty=1.0
        if c.systematic_period_flag: vet_penalty*=.15
        if c.single_epoch_fraction>.75: vet_penalty*=.35
        if c.odd_even_mismatch>4.5: vet_penalty*=.45
        if c.secondary_eclipse_score>4: vet_penalty*=.45
        c.confidence=float(np.clip(p*vet_penalty,.001,.999)); c.ranking_score=c.confidence
    best=max(refined,key=lambda c:c.confidence); threshold=(model.threshold if model else .5); pred=int(best.confidence>=threshold)
    return StarDetectionResult(raw.star_id,pred,float(best.confidence),best.period if pred else None,best.depth_ppm if pred else None,best.duration if pred else None,best,refined,'SUCCESS',runtime_sec=time.perf_counter()-start,cadence_count=raw.original_len,retained_cadence_count=raw.retained_len,provenance={'detrending':det.method,'window_days':det.window_length,'cdpp_ppm':det.cdpp_ppm,'tls_applied':bool(use_tls),'masked_second_pass':bool(candidates),'n_candidates':len(refined),'confidence_source':'raw_ranker' if model and model.ranker is not None else 'physics_heuristic'})
