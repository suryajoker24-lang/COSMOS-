import os, tempfile, uuid
from typing import Optional
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from backend.detect import detect

app=FastAPI(title='COSMOS',version='2.1.0',description='Real Kepler transit detection and characterization API')
app.add_middleware(CORSMiddleware,allow_origins=['*'],allow_methods=['*'],allow_headers=['*'])

@app.get('/health')
def health(): return {'status':'healthy','mode':'REAL','pipeline':'quality -> quarter normalization -> transit-preserving detrending -> BLS -> optional TLS -> vetting -> ranking'}

@app.post('/api/analyze')
async def analyze(file: UploadFile=File(...)):
    name=os.path.basename(file.filename or 'lightcurve.csv')
    if not name.lower().endswith(('.csv','.parquet')): raise HTTPException(400,'Upload CSV or Parquet light curve')
    with tempfile.TemporaryDirectory() as td:
        path=os.path.join(td,name)
        with open(path,'wb') as out: out.write(await file.read())
        result=detect(path)
    result['run_id']=str(uuid.uuid4())[:12]
    return result

@app.post('/api/analyze/path')
def analyze_path(path: str):
    if not os.path.isfile(path): raise HTTPException(404,'File not found')
    return detect(path)
