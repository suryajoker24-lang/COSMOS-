import argparse, json, os
from pipeline import ExoHunterModel, process_star_end_to_end

def main():
    p=argparse.ArgumentParser(prog='cosmos'); sub=p.add_subparsers(dest='command',required=True)
    a=sub.add_parser('analyze'); a.add_argument('--input',required=True)
    sub.add_parser('health')
    args=p.parse_args()
    if args.command=='health': print(json.dumps({'status':'ok','package':'cosmos-exoplanet-detector'})); return
    if args.command=='analyze':
        model=ExoHunterModel('models/candidate_ranker.joblib' if os.path.exists('models/candidate_ranker.joblib') else None)
        print(json.dumps(process_star_end_to_end(args.input,model=model).to_dict(),indent=2))
if __name__=='__main__':main()
