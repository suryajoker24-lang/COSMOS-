# COSMOS REAL DATA AUDIT: Complete System Inventory

**Audit Date**: September 2026  
**Status**: Comprehensive Baseline Completed  
**Objective**: Catalog all mock, hardcoded, synthetic, placeholder, and simulated data sources across COSMOS to execute full conversion into a genuine, data-driven, live scientific application.

---

## Executive Summary of Findings

1. **Dashboard / Mission Control**: Metric cards (PR-AUC, F1, Precision, Recall, Brier score) were hardcoded directly in the HTML markup (`index.html`) with fallback hardcoded values in `app.js` (`0.958`, `0.933`, `94.2%`, `92.5%`). No `/api/metrics` endpoint existed on the backend.
2. **Recent Discoveries / Candidates**: The candidates table in `index.html` contained hardcoded static HTML rows for `KIC_5306984`, `KIC_11442793`, `KIC_10666592`. No `/api/candidates` query endpoint existed to retrieve real vetted candidates from the pipeline or database.
3. **Star Analysis Flow**: `POST /api/analyze/star` was synchronous and blocking. It did not create an asynchronous analysis job (`run_id`), did not report real progressive pipeline stages (`QUEUED`, `LOADING_DATA`, `QUALITY_FILTERING`, `DETRENDING`, `BLS_SEARCH`, `TLS_CONFIRMATION`, `VETTING`, `RANKING`, `COMPLETED`), and did not persist results to a database.
4. **Data Ingestion**: There was no dynamic schema detector, data validator, or light curve adapter (`POST /api/data/upload`) supporting arbitrary CSV/Parquet/FITS files with arbitrary column names.
5. **ASTRA Reasoning & Tools**: The local offline LLM provider contained hardcoded response templates with static strings (e.g., hardcoded `94.4%` precision, `100.0%` recall) and was missing allowlisted action tools (`run_analysis`, `get_analysis_status`, `generate_submission`).
6. **Sky Vision & Plate Solver**: `AstrometryPlateSolver` silently defaulted any image upload to fixed Cygnus Kepler field coordinates (`RA 295.5°`, `Dec 44.5°`) rather than executing actual frame quality checking, star detection, plate solving, and catalog matching.
7. **Sky Journal**: No persistent database storage existed for user notes, observations, saved exoplanet candidates, or star targets.
8. **Submission Generation**: `submission_antigravity.csv` in the root had 89 rows from `data/dev` instead of the competition-specified 87 rows for `data/private_test` (`STAR_0000` to `STAR_0086`).

---

## Detailed Component Audit Matrix

| FILE | COMPONENT | CURRENT DATA SOURCE | MOCK / REAL | REPLACEMENT REQUIRED | PRIORITY |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `frontend/index.html` | Hero PR-AUC Metric (`#statAP`) | Hardcoded HTML string `0.958` | **MOCK** | Fetch live metrics from `GET /api/metrics`; render "Not evaluated" if unavailable | **HIGH** |
| `frontend/index.html` | F1 Harmonic Score (`#statF1`) | Hardcoded HTML string `0.933` | **MOCK** | Populate from `GET /api/metrics` response | **HIGH** |
| `frontend/index.html` | Dev Precision Metric (`#statPrecision`) | Hardcoded HTML string `94.2%` | **MOCK** | Populate from `GET /api/metrics` response | **HIGH** |
| `frontend/index.html` | Dev Recall Metric (`#statRecall`) | Hardcoded HTML string `92.5%` | **MOCK** | Populate from `GET /api/metrics` response | **HIGH** |
| `frontend/index.html` | Top Meta Attributes (Brier, Top-10) | Hardcoded `0.038`, `100.0%` in HTML | **MOCK** | Dynamic display from model evaluation metadata | **MEDIUM** |
| `frontend/index.html` | Recent Candidates Table (`#candidatesTableBody`) | Static HTML rows for `KIC_5306984`, `KIC_11442793`, `KIC_10666592` | **MOCK** | Replace with dynamic table fed by `GET /api/candidates` with search, sort, and status filter | **HIGH** |
| `frontend/index.html` | Telemetry Marquee Ticker | Hardcoded strings referencing specific KIC stars & fake metrics | **MOCK** | Populate from recent analysis events via `GET /api/events/recent` or pipeline telemetry | **MEDIUM** |
| `frontend/index.html` | Photometric Oscilloscope | Hardcoded Mandel-Agol formula & fixed `KIC_5306984` labels | **MOCK** | Connect to active star light curve or clearly label as synthetic instrument test wave | **MEDIUM** |
| `frontend/index.html` | Sidebar Footer Status | Hardcoded `99.98% UP`, `< 1.42s / star` | **MOCK** | Compute uptime & average runtime from actual system health & execution logs | **LOW** |
| `frontend/app.js` | `loadDashboardMetrics()` | Fallback object `{precision: 0.942, recall: 0.925, ...}` | **MOCK** | Strict `GET /api/metrics` call; handle empty / un-evaluated states gracefully without fake numbers | **HIGH** |
| `frontend/app.js` | `renderDifficultyChart()` | Fallback array `[100, 100, 87.5, 85.7]` | **MOCK** | Use actual difficulty bins from backend evaluation metrics or hide if uncomputed | **MEDIUM** |
| `frontend/app.js` | `analyzeStar()` | Synchronous `fetch('/api/lightcurve/{starId}')` with spinner | **SIMULATED** | Asynchronous job creation (`POST /api/analyze/star`), polling or SSE stream of actual stages (`QUEUED` to `COMPLETED`) | **HIGH** |
| `frontend/app.js` | `SKY_OBJECTS` array | Static hardcoded array of 7 objects with 2D canvas pixel coordinates | **STATIC** | Query dynamic astronomical catalog `GET /api/sky/visible` and `GET /api/sky/universe` | **MEDIUM** |
| `frontend/app.js` | `triggerPlateSolve()` | Fixed parameters `hint_ra: 295.5, hint_dec: 44.5`, hardcoded focus to `SKY_OBJECTS[3]` | **MOCK** | Send real image frame / coordinates to `POST /api/sky/solve` or `POST /api/sky/analyze-frame` | **HIGH** |
| `frontend/app.js` | `slewTelescopeToSelected()` | Hardcoded `target_ra: 298.65, target_dec: 44.62` | **MOCK** | Use actual selected object coordinates from astronomical catalog | **MEDIUM** |
| `backend/main.py` | `POST /api/analyze/star` | Blocking handler executing pipeline synchronously; returns ad-hoc JSON | **PARTIAL REAL** | Return `run_id`, launch background worker, stream actual stages, persist run & candidates to DB | **CRITICAL** |
| `backend/main.py` | `GET /api/metrics` | **MISSING** (Endpoint did not exist) | **MISSING** | Implement endpoint calculating/reading actual test/dev evaluation metrics from disk/DB | **HIGH** |
| `backend/main.py` | `GET /api/candidates` | **MISSING** (Endpoint did not exist) | **MISSING** | Implement filterable, sortable candidates endpoint with pagination, SDE, SNR, confidence, and star filters | **HIGH** |
| `backend/main.py` | `GET /api/stars` & `GET /api/stars/{star_id}` | **MISSING** (Endpoint did not exist) | **MISSING** | Implement star catalog listing with metadata, quarters, cadence count, and analysis history | **HIGH** |
| `backend/main.py` | `POST /api/data/upload` | **MISSING** (Endpoint did not exist) | **MISSING** | Implement upload handler with `DataSchemaDetector`, `DataValidator`, and `LightCurveAdapter` for CSV/Parquet/FITS | **CRITICAL** |
| `backend/main.py` | `POST /api/submission` | Defaulted to `data/dev` (89 rows); didn't validate 87-row competition constraint | **MOCK / MISCONFIG** | Enforce 87-row validation on `data/private_test`, validate all characterization columns, return valid CSV download | **HIGH** |
| `backend/main.py` | Database Persistence | None (in-memory state / basic JSON file `jobs_state.json`) | **MOCK** | Implement relational database models (SQLite with PostgreSQL/Neon support) for stars, runs, candidates, journal | **CRITICAL** |
| `backend/jobs.py` | `JobManager` | Unpersisted in-memory lock and unindexed JSON file | **SIMULATED** | Persistent job manager with actual stage tracking, timestamps, errors, reproducibility config hashes | **HIGH** |
| `backend/astra/tools.py` | `get_validation_metrics()` | Fallback static dict with `0.944`, `1.000`, `0.9714`, `0.9856` | **MOCK** | Read actual evaluation files; report real status or `{"evaluated": False}` | **HIGH** |
| `backend/astra/tools.py` | Action Tools | Missing `run_analysis`, `get_analysis_status`, `generate_submission` | **MISSING** | Register allowlisted execution tools with parameter validation | **HIGH** |
| `backend/astra/providers/llm.py` | `LocalMockLLMProvider` | Keyword matching returning hardcoded markdown snippets and canned percentages | **MOCK** | Generate responses dynamically from retrieved tool records; strictly forbid inventing parameters | **HIGH** |
| `backend/astra/astronomy/plate_solver.py` | `AstrometryPlateSolver` | Hardcodes Cygnus RA/Dec if image bytes provided | **MOCK** | Real image analysis: luminance histogram, star centroiding, catalog pattern matching, or honest failure ("Unable to confidently solve") | **HIGH** |
| `backend/astra/astronomy/telescope.py` | `MockTelescopeProvider` | Simulates slew without hardware verification | **SIMULATED** | Clear labeling as simulation provider; support ASCOM/INDI interfaces | **LOW** |
| `backend/astra/journal.py` | Sky Discovery Journal | Missing backend persistence layer | **MISSING** | Implement CRUD journal service with SQLite/Postgres persistence, tagging, notes, and exoplanet linking | **HIGH** |
| `submission_antigravity.csv` | Competition Submission | Contained 89 rows from `data/dev` with KIC star IDs | **INCORRECT** | Regenerate on `data/private_test` with 87 rows (`STAR_0000` to `STAR_0086`), strict columns and validated parameters | **HIGH** |

---

## Key Replacement Directives

1. **Strict Real vs Demo Mode**:
   - Every API response and UI component must indicate `mode: "REAL"` or `mode: "DEMO"`.
   - Never silently substitute fake candidate results if pipeline analysis fails; report the real scientific error message.
2. **Asynchronous Job Pipeline**:
   - Analysis of stars (which takes 2–15 seconds per star for detrending, BLS, and TLS) must be executed in background worker tasks.
   - Stage progress must be factual (`QUEUED` -> `LOADING_DATA` -> `QUALITY_FILTERING` -> `DETRENDING` -> `BLS_SEARCH` -> `TLS_CONFIRMATION` -> `VETTING` -> `RANKING` -> `COMPLETED`).
3. **Dynamic Arbitrary Data Ingestion**:
   - Add `DataSchemaDetector` and `LightCurveAdapter` that inspect arbitrary uploaded CSV/Parquet files, detect time/flux/error/quality columns, calculate time baseline, cadence, and missing values, and pass them into the scientific pipeline.
4. **Tool-Grounded ASTRA**:
   - ASTRA must invoke allowlisted backend tools to retrieve star light curves, candidates, and metrics.
   - If data does not exist for a star, ASTRA must state that rather than fabricating orbital periods or depths.
5. **Real Database Layer**:
   - Store metadata in a robust database (SQLite local with auto-detection of PostgreSQL/Neon `DATABASE_URL` for production).
   - Track `run_id`, `config_hash`, `pipeline_version`, and execution duration for full scientific reproducibility.
6. **Preserve Visual Design & Launch Page**:
   - The launch page (`landing.html`, `landing.js`, `particleEngine.js`) remains completely untouched.
   - The styling, dark palette, glass panels, and typography in `index.html` are strictly preserved while binding the elements to live APIs.
