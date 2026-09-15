# FastAPI Schemas and Persistent Job Manager
import os
import uuid
import time
import json
import threading
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from backend.database import SessionLocal, AnalysisRun, AnalysisEvent

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
                self.jobs[job_id]["elapsed_seconds"] = round(time.time() - self.jobs[job_id]["created_at"], 2)
                self._save()

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        # 1. Check in-memory batch jobs
        with self.lock:
            if job_id in self.jobs:
                return self.jobs[job_id]

        # 2. Check Database AnalysisRuns for single-star or upload runs
        db = SessionLocal()
        try:
            run_obj = db.query(AnalysisRun).filter(AnalysisRun.id == job_id).first()
            if run_obj:
                events = db.query(AnalysisEvent).filter(AnalysisEvent.run_id == job_id).order_by(AnalysisEvent.timestamp.asc()).all()
                result_data = json.loads(run_obj.result_json) if run_obj.result_json else None
                latest_event = events[-1].message if events else run_obj.status
                latest_progress = events[-1].progress_pct if events else 0.0

                elapsed = run_obj.duration_sec if run_obj.duration_sec is not None else round(time.time() - run_obj.created_at, 2)
                
                return {
                    "job_id": run_obj.id,
                    "star_id": run_obj.star_id,
                    "job_type": "star_analysis",
                    "status": run_obj.status,
                    "stage": events[-1].stage if events else run_obj.status,
                    "message": latest_event,
                    "progress": round(latest_progress / 100.0, 2),
                    "total_stars": 1,
                    "completed_stars": 1 if run_obj.status == "COMPLETED" else 0,
                    "created_at": run_obj.created_at,
                    "elapsed_seconds": elapsed,
                    "is_cached": run_obj.is_cached,
                    "errors": [run_obj.error] if run_obj.error else [],
                    "events": [
                        {
                            "stage": e.stage,
                            "message": e.message,
                            "progress_pct": e.progress_pct,
                            "timestamp": e.timestamp
                        }
                        for e in events
                    ],
                    "results": [result_data] if result_data else []
                }
            return None
        finally:
            db.close()

job_manager = JobManager()
