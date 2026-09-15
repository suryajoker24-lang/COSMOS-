"""Train COSMOS candidate ranker with star-grouped CV and correct label/truth semantics."""
import argparse, glob, json, os
import numpy as np
import pandas as pd
from sklearn.model_selection import GroupKFold
from sklearn.metrics import average_precision_score, f1_score, precision_score, recall_score
from pipeline import load_raw_lightcurve, preprocess_lightcurve, detrend_lightcurve, search_candidates_bls, refine_candidate_tls, vet_candidate, extract_candidate_features, features_dict_to_dataframe
from pipeline.features import FEATURE_NAMES

try:
    import lightgbm as lgb
except ImportError as exc:
    raise SystemExit('Install lightgbm before training the ranker') from exc

ALIASES=(1.0,2.0,.5,3.0,1/3,1.5,2/3,2.5,.4)

def period_match(p,true_p):
    if not p or not true_p:return False
    return any(abs(p/true_p-a)<.02 for a in ALIASES)

def load_truth_maps(pack_dir):
    labels=pd.read_csv(os.path.join(pack_dir,'train_labels.csv'))
    truth=pd.read_csv(os.path.join(pack_dir,'train_truth.csv'))
    injected={int(r.kepid):r for _,r in truth.iterrows() if int(r.get('injected',1))==1}
    real=set(int(x) for x in labels.loc[labels['label']==1,'kepid'])
    return real,injected

def build_dataset(pack_dir):
    star_dir=os.path.join(pack_dir,'train')
    real,injected=load_truth_maps(pack_dir)
    X=[]; y=[]; groups=[]
    for idx,path in enumerate(sorted(glob.glob(os.path.join(star_dir,'*.parquet')))):
        kepid=int(os.path.splitext(os.path.basename(path))[0].replace('KIC_',''))
        has_planet=(kepid in real) or (kepid in injected)
        raw=load_raw_lightcurve(path); pre=preprocess_lightcurve(raw); det=detrend_lightcurve(pre,window_length=.75)
        cands=search_candidates_bls(det,min_period=.5,max_period=None,top_k=7)
        if not cands: continue
        truth_row=injected.get(kepid)
        for cand in cands:
            cand=refine_candidate_tls(det,cand); cand=vet_candidate(det,cand,pre.quarter)
            feats=extract_candidate_features(cand,det,pre)
            if not has_planet: label=0
            elif truth_row is not None: label=int(period_match(cand.period,float(truth_row['period_days'])))
            else: label=1
            X.append(feats); y.append(label); groups.append(idx)
    df=features_dict_to_dataframe(X)
    return df,np.asarray(y),np.asarray(groups)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--pack-dir',required=True); ap.add_argument('--out',default='models/candidate_ranker.joblib'); args=ap.parse_args()
    X,y,g=build_dataset(args.pack_dir)
    if y.sum()<5 or len(np.unique(g))<5: raise SystemExit('Insufficient training groups/positives')
    oof=np.zeros(len(y)); cv=GroupKFold(5)
    for tr,va in cv.split(X,y,g):
        m=lgb.LGBMClassifier(n_estimators=220,learning_rate=.035,num_leaves=15,max_depth=4,min_child_samples=8,subsample=.85,colsample_bytree=.85,random_state=42,verbosity=-1)
        m.fit(X.iloc[tr],y[tr]); oof[va]=m.predict_proba(X.iloc[va])[:,1]
    best=(.5,0)
    for th in np.linspace(.05,.95,181):
        f=f1_score(y,oof>=th,zero_division=0)
        if f>best[1]:best=(float(th),float(f))
    final=lgb.LGBMClassifier(n_estimators=260,learning_rate=.03,num_leaves=15,max_depth=4,min_child_samples=8,subsample=.85,colsample_bytree=.85,random_state=42,verbosity=-1)
    final.fit(X,y)
    os.makedirs(os.path.dirname(args.out) or '.',exist_ok=True)
    import joblib
    joblib.dump({'ranker':final,'calibrator':None,'threshold':best[0]},args.out)
    metrics={'samples':len(y),'positive_candidates':int(y.sum()),'groups':int(len(np.unique(g))),'average_precision':float(average_precision_score(y,oof)),'precision_at_threshold':float(precision_score(y,oof>=best[0],zero_division=0)),'recall_at_threshold':float(recall_score(y,oof>=best[0],zero_division=0)),'f1_at_threshold':best[1],'threshold':best[0]}
    with open(os.path.splitext(args.out)[0]+'.metrics.json','w') as f:json.dump(metrics,f,indent=2)
    print(json.dumps(metrics,indent=2))
if __name__=='__main__':main()
