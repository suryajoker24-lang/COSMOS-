# Database Models and Session Management for COSMOS
import os
import time
import json
import uuid
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from sqlalchemy import (
    create_engine, Column, String, Integer, Float, Boolean, Text, ForeignKey, Index, DateTime
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship, Session
from sqlalchemy.pool import StaticPool

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    # Default to persistent local SQLite database
    os.makedirs("data", exist_ok=True)
    DATABASE_URL = "sqlite:///data/cosmos.db"

# Handle sqlite specific connect args
connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}
    engine = create_engine(DATABASE_URL, connect_args=connect_args)
else:
    # PostgreSQL / Neon configuration
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Star(Base):
    __tablename__ = "stars"
    
    star_id = Column(String(64), primary_key=True, index=True)
    kepid = Column(Integer, nullable=True, index=True)
    source = Column(String(32), default="kepler_primary")  # train, dev, private_test, upload
    quarters_count = Column(Integer, default=0)
    cadences = Column(Integer, default=0)
    baseline_days = Column(Float, default=0.0)
    created_at = Column(Float, default=time.time)

    light_curves = relationship("LightCurveMeta", back_populates="star", cascade="all, delete-orphan")
    runs = relationship("AnalysisRun", back_populates="star", cascade="all, delete-orphan")

class LightCurveMeta(Base):
    __tablename__ = "light_curves_meta"

    id = Column(Integer, primary_key=True, autoincrement=True)
    star_id = Column(String(64), ForeignKey("stars.star_id"), index=True)
    file_path = Column(String(256), nullable=False)
    file_format = Column(String(16), default="parquet")  # parquet, csv, fits
    file_size_bytes = Column(Integer, default=0)
    num_rows = Column(Integer, default=0)
    time_min = Column(Float, nullable=True)
    time_max = Column(Float, nullable=True)
    cadence_min = Column(Float, default=29.4)
    uploaded_at = Column(Float, default=time.time)

    star = relationship("Star", back_populates="light_curves")

class AnalysisRun(Base):
    __tablename__ = "analysis_runs"

    id = Column(String(64), primary_key=True, index=True)  # UUID
    star_id = Column(String(64), ForeignKey("stars.star_id"), nullable=True, index=True)
    status = Column(String(32), default="QUEUED", index=True)
    created_at = Column(Float, default=time.time)
    completed_at = Column(Float, nullable=True)
    duration_sec = Column(Float, nullable=True)
    pipeline_version = Column(String(32), default="v1.0")
    config_hash = Column(String(64), index=True)
    configuration_json = Column(Text, default="{}")
    error = Column(Text, nullable=True)
    prediction = Column(Integer, nullable=True)
    confidence = Column(Float, nullable=True)
    period = Column(Float, nullable=True)
    depth_ppm = Column(Float, nullable=True)
    duration_hours = Column(Float, nullable=True)
    is_cached = Column(Boolean, default=False)
    result_json = Column(Text, nullable=True)

    star = relationship("Star", back_populates="runs")
    candidates = relationship("Candidate", back_populates="run", cascade="all, delete-orphan")
    events = relationship("AnalysisEvent", back_populates="run", cascade="all, delete-orphan")

class Candidate(Base):
    __tablename__ = "candidates"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String(64), ForeignKey("analysis_runs.id"), index=True)
    star_id = Column(String(64), index=True)
    candidate_index = Column(Integer, default=0)
    period = Column(Float, nullable=False)
    depth_ppm = Column(Float, nullable=False)
    duration_hours = Column(Float, nullable=False)
    epoch_t0 = Column(Float, nullable=False)
    sde = Column(Float, default=0.0)
    snr = Column(Float, default=0.0)
    odd_even_consistency = Column(Float, default=1.0)
    secondary_eclipse_score = Column(Float, default=0.0)
    quarter_recurrence_fraction = Column(Float, default=1.0)
    calibrated_confidence = Column(Float, default=0.0, index=True)
    ml_score = Column(Float, default=0.0)
    alias_type = Column(String(32), default="none")

    run = relationship("AnalysisRun", back_populates="candidates")
    features = relationship("CandidateFeature", back_populates="candidate", cascade="all, delete-orphan")
    vetting_results = relationship("VettingResult", back_populates="candidate", cascade="all, delete-orphan")

class CandidateFeature(Base):
    __tablename__ = "candidate_features"

    id = Column(Integer, primary_key=True, autoincrement=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id"), index=True)
    feature_name = Column(String(64), nullable=False)
    feature_value = Column(Float, nullable=False)

    candidate = relationship("Candidate", back_populates="features")

class VettingResult(Base):
    __tablename__ = "vetting_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id"), index=True)
    test_name = Column(String(64), nullable=False)
    passed = Column(Boolean, default=True)
    statistic = Column(Float, nullable=True)
    threshold = Column(Float, nullable=True)
    notes = Column(String(256), nullable=True)

    candidate = relationship("Candidate", back_populates="vetting_results")

class AnalysisEvent(Base):
    __tablename__ = "analysis_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String(64), ForeignKey("analysis_runs.id"), index=True)
    stage = Column(String(32), nullable=False)
    message = Column(String(256), nullable=False)
    progress_pct = Column(Float, default=0.0)
    timestamp = Column(Float, default=time.time)

    run = relationship("AnalysisRun", back_populates="events")

class JournalEntry(Base):
    __tablename__ = "journal_entries"

    id = Column(String(64), primary_key=True, index=True)  # UUID
    star_id = Column(String(64), nullable=True, index=True)
    object_name = Column(String(128), nullable=False)
    object_type = Column(String(64), default="Target Star")
    constellation = Column(String(64), default="Cygnus")
    notes = Column(Text, default="")
    ra_deg = Column(Float, nullable=True)
    dec_deg = Column(Float, nullable=True)
    is_kepler_candidate = Column(Boolean, default=False)
    created_at = Column(Float, default=time.time)
    updated_at = Column(Float, default=time.time)
    tags = Column(String(256), default="")

class SavedObject(Base):
    __tablename__ = "saved_objects"

    id = Column(String(64), primary_key=True, index=True)
    name = Column(String(128), nullable=False, unique=True)
    ra_deg = Column(Float, nullable=False)
    dec_deg = Column(Float, nullable=False)
    catalog_source = Column(String(64), default="Kepler Primary Survey")
    object_type = Column(String(64), default="Star")
    magnitude = Column(Float, nullable=True)
    meta_json = Column(Text, default="{}")
    created_at = Column(Float, default=time.time)

class NASAValidation(Base):
    __tablename__ = "nasa_validations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    analysis_run_id = Column(String(64), nullable=True, index=True)
    star_id = Column(String(64), nullable=False, index=True)
    kic_id = Column(Integer, nullable=False, index=True)
    nasa_lookup_status = Column(String(32), default="SUCCESS")  # SUCCESS, NOT_FOUND, ERROR

    koi_records = Column(Text, default="[]")       # JSON array of KOI records
    tce_records = Column(Text, default="[]")       # JSON array of TCE records
    planet_records = Column(Text, default="[]")    # JSON array of Confirmed Planets
    stellar_record = Column(Text, default="{}")    # JSON object of stellar params

    cosmos_period = Column(Float, nullable=True)
    nasa_period = Column(Float, nullable=True)
    period_difference = Column(Float, nullable=True)
    harmonic_relation = Column(String(32), default="NONE")  # DIRECT, 1/2, 2x, 1/3, 3x, etc.

    cosmos_depth_ppm = Column(Float, nullable=True)
    nasa_depth_ppm = Column(Float, nullable=True)

    cosmos_duration_hours = Column(Float, nullable=True)
    nasa_duration_hours = Column(Float, nullable=True)

    phase_difference = Column(Float, nullable=True)
    mast_available = Column(Boolean, default=False)
    mast_match_score = Column(Float, default=0.0)

    validation_status = Column(String(32), nullable=False, index=True)  # NASA VERIFIED, NASA CONFLICT, UNVERIFIED
    validation_reason = Column(Text, nullable=False)
    source_urls = Column(Text, default="{}")  # JSON map of URLs

    retrieved_at = Column(Float, default=time.time)
    validator_version = Column(String(32), default="COSMOS-NASA-Validator-v1.0")

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Helper utilities
def find_cached_run(db: Session, star_id: str, config_hash: str) -> Optional[AnalysisRun]:
    return db.query(AnalysisRun).filter(
        AnalysisRun.star_id == star_id,
        AnalysisRun.config_hash == config_hash,
        AnalysisRun.status == "COMPLETED"
    ).order_by(AnalysisRun.created_at.desc()).first()

def log_event(db: Session, run_id: str, stage: str, message: str, progress_pct: float = 0.0):
    ev = AnalysisEvent(
        run_id=run_id,
        stage=stage,
        message=message,
        progress_pct=progress_pct,
        timestamp=time.time()
    )
    db.add(ev)
    db.commit()
