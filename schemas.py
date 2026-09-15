# FastAPI schemas and Job manager
import os
import uuid
import time
import json
import threading
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class CandidateInfo(BaseModel):
    star_id: str
    kepid: int
    period: float
    epoch_t0: float
    duration_hours: float
    depth_ppm: float
    sde: float
    bls_power: float
    transit_count: int
    odd_even_consistency: float
    secondary_eclipse_score: float
    quarter_recurrence_fraction: float
    in_transit_points: int
    phase_coverage: float
    transit_snr: float
    ml_score: float
    calibrated_confidence: float
    alias_type: str

class StarAnalysisResponse(BaseModel):
    star_id: str
    kepid: int
    prediction: int
    confidence: float
    period: Optional[float] = None
    depth_ppm: Optional[float] = None
    duration_hours: Optional[float] = None
    candidate: Optional[CandidateInfo] = None
    all_candidates: List[CandidateInfo] = Field(default_factory=list)

class BatchJobResponse(BaseModel):
    job_id: str
    status: str
    message: str
    created_at: float

class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    progress: float
    total_stars: int
    completed_stars: int
    elapsed_seconds: float
    errors: List[str] = Field(default_factory=list)
    results: Optional[List[Dict[str, Any]]] = None

class JobManager:
    def __init__(self, state_file: str = "backend/jobs_state.json"):
        self.state_file = state_file
        self.jobs: Dict[str, Dict[str, Any]] = {}
        self.lock = threading.Lock()
        self._load()
        
    def _load(self):
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    self.jobs = json.load(f)
            except Exception:
                self.jobs = {}
                
    def _save(self):
        os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
        try:
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(self.jobs, f, indent=2)
        except Exception:
            pass

    def create_job(self, job_type: str, total_stars: int = 0) -> str:
        with self.lock:
            job_id = str(uuid.uuid4())[:8]
            self.jobs[job_id] = {
                "job_id": job_id,
                "job_type": job_type,
                "status": "queued",
                "progress": 0.0,
                "total_stars": total_stars,
                "completed_stars": 0,
                "created_at": time.time(),
                "updated_at": time.time(),
                "elapsed_seconds": 0.0,
                "errors": [],
                "results": []
            }
            self._save()
            return job_id

    def update_job(self, job_id: str, **kwargs):
        with self.lock:
            if job_id in self.jobs:
                self.jobs[job_id].update(kwargs)
                self.jobs[job_id]["updated_at"] = time.time()
                self.jobs[job_id]["elapsed_seconds"] = self.jobs[job_id]["updated_at"] - self.jobs[job_id]["created_at"]
                self._save()

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        with self.lock:
            return self.jobs.get(job_id)

job_manager = JobManager()
