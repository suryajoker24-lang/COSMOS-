# Baseline Pipeline Execution Script
import os
import glob
import time
import json
import warnings
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from astropy.timeseries import BoxLeastSquares
from concurrent.futures import ProcessPoolExecutor, as_completed
from sklearn.metrics import precision_score, recall_score, f1_score, average_precision_score, precision_recall_curve, roc_auc_score

warnings.filterwarnings('ignore')

DETREND_WINDOW_DAYS = 1.0
PERIOD_MIN = 3.0
PERIOD_MAX = 400.0
N_COARSE = 20000
N_PEAKS = 8
N_FINE = 600
DURATIONS = np.array([0.05, 0.1, 0.2, 0.4, 0.8])
SDE_THRESHOLD = 10.0

def clean(df, window_days=DETREND_WINDOW_DAYS):
    m = (df.quality.values == 0) & np.isfinite(df.flux.values)
    t = df.time.values[m]
    f = df.flux.values[m].astype(float)
    q = df.quarter.values[m]
    if len(t) < 1000:
        return None, None
    for qq in np.unique(q):
        s = q == qq
        med = np.median(f[s])
        f[s] = f[s] / med if med > 0 else 1.0
    cadence = np.median(np.diff(t))
    k = max(5, int(window_days / cadence) | 1)
    trend = pd.Series(f).rolling(k, center=True, min_periods=k // 3).median().values
    ok = np.isfinite(trend) & (trend > 0)
    return t[ok], f[ok] / trend[ok]

def sde(power, i):
    med = np.nanmedian(power)
    mad = np.nanmedian(np.abs(power - med))
    return float((power[i] - med) / (1.4826 * mad)) if mad > 0 else 0.0

def search(t, f):
    bls = BoxLeastSquares(t, f)
    baseline = t.max() - t.min()
    pmax = min(PERIOD_MAX, baseline / 3.0)
    if pmax <= PERIOD_MIN:
        return {'period': np.nan, 'depth_ppm': np.nan, 'duration_hours': np.nan, 't0': np.nan, 'sde': 0.0}
    coarse = np.exp(np.linspace(np.log(PERIOD_MIN), np.log(pmax), N_COARSE))
    res = bls.power(coarse, DURATIONS, objective='likelihood')
    power = np.asarray(res.power)
    order = np.argsort(power)[::-1]
    peaks, used = [], np.zeros(len(coarse), bool)
    for i in order:
        if used[i]:
            continue
        peaks.append(i)
        lo = np.searchsorted(coarse, coarse[i] * 0.9)
        hi = np.searchsorted(coarse, coarse[i] * 1.1)
        used[lo:hi] = True
        if len(peaks) >= N_PEAKS:
            break
    best = None
    for i in peaks:
        p0 = coarse[i]
        width = 0.02 * p0
        fine = np.linspace(p0 - width, p0 + width, N_FINE)
        fine = fine[fine > PERIOD_MIN]
        if len(fine) < 10:
            continue
        r = bls.power(fine, DURATIONS, objective='likelihood')
        p = np.asarray(r.power)
        j = int(np.nanargmax(p))
        score = sde(power, i)
        if best is None or score > best['sde']:
            best = {
                'period': float(r.period[j]),
                'depth_ppm': float(r.depth[j] * 1e6),
                'duration_hours': float(r.duration[j] * 24),
                't0': float(r.transit_time[j]),
                'sde': score,
            }
    return best or {'period': np.nan, 'depth_ppm': np.nan, 'duration_hours': np.nan, 't0': np.nan, 'sde': 0.0}

def confidence_from_sde(s, midpoint=SDE_THRESHOLD, steepness=0.4):
    return float(1.0 / (1.0 + np.exp(-steepness * (s - midpoint))))

def process_star(path):
    sid = os.path.basename(path).replace('.parquet', '')
    kepid = int(sid.replace('KIC_', ''))
    try:
        df = pd.read_parquet(path)
        t, f = clean(df)
        if t is None:
            r = {'period': np.nan, 'depth_ppm': np.nan, 'duration_hours': np.nan, 't0': np.nan, 'sde': 0.0}
        else:
            r = search(t, f)
    except Exception as e:
        r = {'period': np.nan, 'depth_ppm': np.nan, 'duration_hours': np.nan, 't0': np.nan, 'sde': 0.0}
    s = r.get('sde', 0.0)
    hit = s > SDE_THRESHOLD
    return {
        'star_id': sid,
        'kepid': kepid,
        'prediction': int(hit),
        'confidence': float(round(confidence_from_sde(s), 4)),
        'period': float(round(r['period'], 5)) if hit and np.isfinite(r['period']) else np.nan,
        'depth_ppm': float(round(r['depth_ppm'], 1)) if hit and np.isfinite(r['depth_ppm']) else np.nan,
        'duration_hours': float(round(r['duration_hours'], 3)) if hit and np.isfinite(r['duration_hours']) else np.nan,
        'sde': float(round(s, 2)),
        't0': float(r.get('t0', np.nan))
    }

def main():
    os.makedirs('results/baseline', exist_ok=True)
    dev_paths = sorted(glob.glob('data/dev/*.parquet'))
    n_total = len(dev_paths)
    workers = min(8, max(1, (os.cpu_count() or 4) - 1))
    print(f'Starting baseline search on {n_total} dev stars using {workers} workers...', flush=True)
    t0 = time.time()
    
    results = []
    with ProcessPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(process_star, p): p for p in dev_paths}
        done_count = 0
        for fut in as_completed(futures):
            res = fut.result()
            results.append(res)
            done_count += 1
            if done_count % 10 == 0 or done_count == n_total:
                print(f'  [{done_count}/{n_total}] Completed in {time.time()-t0:.1f}s...', flush=True)
    
    elapsed = time.time() - t0
    print(f'All {n_total} stars completed in {elapsed:.1f}s ({elapsed/n_total:.2f}s per star)', flush=True)
    
    df_res = pd.DataFrame(results).sort_values('star_id').reset_index(drop=True)
    labels = pd.read_csv('data/dev_labels.csv')
    truth = pd.read_csv('data/dev_truth.csv')
    
    df_res = df_res.merge(labels[['kepid', 'label', 'koi_disposition']], on='kepid', how='left')
    df_res = df_res.merge(truth[['kepid', 'injected', 'bin', 'period_days', 'depth_ppm', 'duration_hours']],
                          on='kepid', how='left', suffixes=('', '_true'))
    df_res['injected'] = df_res['injected'].fillna(0).astype(int)
    df_res['has_planet'] = ((df_res['label'] == 1) | (df_res['injected'] == 1)).astype(int)
    
    df_res.to_csv('results/baseline/predictions.csv', index=False)
    
    y_true = df_res['has_planet'].values
    y_pred = df_res['prediction'].values
    y_conf = df_res['confidence'].values
    
    prec = precision_score(y_true, y_pred, zero_division=0)
    rec = recall_score(y_true, y_pred, zero_division=0)
    f1 = f1_score(y_true, y_pred, zero_division=0)
    ap = average_precision_score(y_true, y_conf)
    roc_auc = roc_auc_score(y_true, y_conf)
    
    bins = ['deep', 'mid', 'shallow', 'earth_analog']
    bin_metrics = {}
    for b in bins:
        sub_b = df_res[df_res['bin'] == b]
        if len(sub_b) > 0:
            rec_b = (sub_b['prediction'] == 1).mean()
            bin_metrics[b] = {
                'count': int(len(sub_b)),
                'recovered_count': int((sub_b['prediction'] == 1).sum()),
                'recall': float(round(rec_b, 4))
            }
    
    inj_eval = df_res[(df_res['injected'] == 1) & (df_res['prediction'] == 1) & df_res['period'].notna()]
    period_hits = 0
    depth_rel_errors = []
    
    for _, row in inj_eval.iterrows():
        p_rec = row['period']
        p_true = row['period_days']
        aliases = [p_true, p_true / 2.0, p_true * 2.0, p_true / 3.0, p_true * 3.0]
        min_err = min([abs(p_rec - a) / a for a in aliases])
        if min_err <= 0.02:
            period_hits += 1
        d_rec = row['depth_ppm']
        d_true = row['depth_ppm_true']
        if d_true > 0:
            depth_rel_errors.append(abs(d_rec - d_true) / d_true)
            
    period_acc = period_hits / len(df_res[df_res['injected'] == 1])
    depth_mre = float(np.mean(depth_rel_errors)) if depth_rel_errors else np.nan
    depth_med_re = float(np.median(depth_rel_errors)) if depth_rel_errors else np.nan
    
    metrics = {
        'split': 'dev',
        'n_stars': int(len(df_res)),
        'n_positives': int(y_true.sum()),
        'n_negatives': int((y_true == 0).sum()),
        'elapsed_seconds': round(elapsed, 2),
        'seconds_per_star': round(elapsed / len(df_res), 2),
        'precision': round(prec, 4),
        'recall': round(rec, 4),
        'f1': round(f1, 4),
        'average_precision': round(ap, 4),
        'roc_auc': round(roc_auc, 4),
        'period_recovery_rate_injected': round(period_acc, 4),
        'mean_relative_depth_error': round(depth_mre, 4) if np.isfinite(depth_mre) else None,
        'median_relative_depth_error': round(depth_med_re, 4) if np.isfinite(depth_med_re) else None,
        'difficulty_bins': bin_metrics
    }
    
    with open('results/baseline/metrics.json', 'w') as f:
        json.dump(metrics, f, indent=2)
        
    print('\n=== BASELINE RESULTS (DEV SET) ===', flush=True)
    print(json.dumps(metrics, indent=2), flush=True)
    
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    axes[0].hist(df_res[df_res['has_planet'] == 0]['sde'], bins=20, alpha=0.6, label='Clean Stars (No Planet)', color='steelblue')
    axes[0].hist(df_res[df_res['has_planet'] == 1]['sde'], bins=20, alpha=0.6, label='Planet Stars', color='crimson')
    axes[0].axvline(SDE_THRESHOLD, color='black', linestyle='--', label=f'Baseline Cut (SDE={SDE_THRESHOLD})')
    axes[0].set_xlabel('BLS SDE')
    axes[0].set_ylabel('Count')
    axes[0].set_title('Baseline SDE Distribution')
    axes[0].legend()
    
    p_curve, r_curve, _ = precision_recall_curve(y_true, y_conf)
    axes[1].plot(r_curve, p_curve, color='darkorange', lw=2, label=f'AP = {ap:.3f}')
    axes[1].set_xlabel('Recall')
    axes[1].set_ylabel('Precision')
    axes[1].set_title('Baseline Precision-Recall Curve')
    axes[1].set_xlim([0.0, 1.05])
    axes[1].set_ylim([0.0, 1.05])
    axes[1].legend(loc='lower left')
    axes[1].grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('results/baseline/baseline_performance.png', dpi=150)
    plt.close()
    print('Saved baseline diagnostic plot to results/baseline/baseline_performance.png', flush=True)

if __name__ == '__main__':
    main()
