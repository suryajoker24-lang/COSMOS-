import os
import pandas as pd
from pipeline.models import StarDetectionResult
REQUIRED_COLUMNS=['star_id','prediction','confidence','period','depth_ppm','duration_hours']

def results_to_submission_dataframe(results):
    rows=[]
    for r in results:
        rows.append({'star_id':r.star_id,'prediction':int(r.prediction),'confidence':round(float(r.confidence),6),'period':round(float(r.period),6) if r.prediction and r.period is not None else '','depth_ppm':round(float(r.depth_ppm),2) if r.prediction and r.depth_ppm is not None else '','duration_hours':round(float(r.duration_hours),4) if r.prediction and r.duration_hours is not None else ''})
    return pd.DataFrame(rows,columns=REQUIRED_COLUMNS)

def validate_submission_dataframe(df,expected_rows=None):
    if list(df.columns)!=REQUIRED_COLUMNS: raise ValueError(f'Columns must be exactly {REQUIRED_COLUMNS}')
    if df['star_id'].duplicated().any(): raise ValueError('Duplicate star_id values')
    if expected_rows is not None and len(df)!=expected_rows: raise ValueError(f'Expected {expected_rows} rows, got {len(df)}')
    if not df['prediction'].isin([0,1]).all(): raise ValueError('prediction must be 0 or 1')
    if not df['confidence'].between(0,1).all(): raise ValueError('confidence must be in [0,1]')
    pos=df.prediction==1; neg=~pos
    for c in ('period','depth_ppm','duration_hours'):
        if df.loc[pos,c].isna().any(): raise ValueError(f'{c} missing for a positive prediction')
        if df.loc[neg,c].notna().any(): raise ValueError(f'{c} must be blank for prediction=0')
    if (df.loc[pos,'period']<=0).any(): raise ValueError('period must be positive')
    return True

def save_submission_file(df,output_path,expected_rows=None):
    validate_submission_dataframe(df,expected_rows)
    os.makedirs(os.path.dirname(os.path.abspath(output_path)),exist_ok=True)
    df.to_csv(output_path,index=False)
    # Re-read to ensure blanks remain blanks on disk.
    check=pd.read_csv(output_path,keep_default_na=True)
    validate_submission_dataframe(check,expected_rows)
    return output_path
