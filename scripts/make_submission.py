import argparse, glob, os
from pipeline import ExoHunterModel, process_star_end_to_end, results_to_submission_dataframe, save_submission_file

def main():
    p=argparse.ArgumentParser(); p.add_argument('--pack-dir',required=True,help='Directory containing STAR_*.parquet or KIC_*.parquet'); p.add_argument('--team',default='cosmos'); p.add_argument('--out',default=None); p.add_argument('--threshold',type=float,default=None); args=p.parse_args()
    paths=sorted(glob.glob(os.path.join(args.pack_dir,'*.parquet'))+glob.glob(os.path.join(args.pack_dir,'*.csv')))
    if not paths: raise SystemExit('No CSV/Parquet light curves found')
    model=ExoHunterModel('models/candidate_ranker.joblib' if os.path.exists('models/candidate_ranker.joblib') else None)
    if args.threshold is not None:model.threshold=args.threshold
    results=[process_star_end_to_end(x,model=model,use_tls=True) for x in paths]
    df=results_to_submission_dataframe(results)
    out=args.out or f'submission_{args.team.lower().replace(" ","_")}.csv'
    save_submission_file(df,out,expected_rows=87 if 'private' in args.pack_dir.lower() else None)
    print(f'Wrote {out}: {len(df)} stars, {int(df.prediction.sum())} detections')
if __name__=='__main__':main()
