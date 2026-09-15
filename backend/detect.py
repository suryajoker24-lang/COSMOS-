import os
from typing import Dict, Any
from pipeline import ExoHunterModel, process_star_end_to_end

_MODEL=None

def _get_model():
    global _MODEL
    if _MODEL is None:
        path=os.path.join(os.path.dirname(os.path.dirname(__file__)),'models','candidate_ranker.joblib')
        _MODEL=ExoHunterModel(path if os.path.exists(path) else None)
    return _MODEL

def detect(filepath: str) -> Dict[str, Any]:
    try:
        result=process_star_end_to_end(filepath,model=_get_model(),use_tls=True)
        return result.to_dict()
    except Exception as exc:
        sid=os.path.splitext(os.path.basename(filepath))[0]
        return {'star_id':sid,'prediction':0,'confidence':0.001,'period':None,'depth_ppm':None,'duration_hours':None,'status':'FAILED','error_message':str(exc),'candidates':[]}
