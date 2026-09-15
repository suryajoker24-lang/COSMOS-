// COSMOS Frontend Scientific API Client Layer
// Provides uniform loading, error handling, and separation of UI from API logic

const API = {
    // 1. System Health & Evaluation Metrics
    metrics: {
        async get() {
            const res = await fetch("/api/metrics");
            if (!res.ok) throw new Error(`Failed to fetch metrics: ${res.statusText}`);
            return await res.json();
        },
        async getModelInfo() {
            const res = await fetch("/api/models");
            if (!res.ok) throw new Error(`Failed to fetch model info: ${res.statusText}`);
            return await res.json();
        },
        async getHealth() {
            const res = await fetch("/health");
            if (!res.ok) throw new Error(`Failed to fetch health: ${res.statusText}`);
            return await res.json();
        }
    },

    models: {
        async info() {
            const res = await fetch("/api/models");
            if (!res.ok) throw new Error(`Failed to fetch model info: ${res.statusText}`);
            return await res.json();
        }
    },

    lightcurve: {
        async get(starId) {
            const res = await fetch(`/api/lightcurve/${encodeURIComponent(starId)}`);
            if (!res.ok) {
                const errData = await res.json().catch(() => ({}));
                throw new Error(errData.detail || `Star ${starId} lightcurve failed to load.`);
            }
            return await res.json();
        }
    },

    validation: {
        async get(starId, period = null, depth = null, duration = null) {
            const params = new URLSearchParams();
            if (period != null) params.append("period", period);
            if (depth != null) params.append("depth", depth);
            if (duration != null) params.append("duration", duration);
            const q = params.toString() ? `?${params.toString()}` : "";
            const res = await fetch(`/api/validate/${encodeURIComponent(starId)}${q}`);
            if (!res.ok) return { status: "error", message: res.statusText };
            return await res.json();
        }
    },

    // 2. Star Catalog & Discovery
    stars: {
        async list(query = "", limit = 50, offset = 0) {
            const q = query ? `&query=${encodeURIComponent(query)}` : "";
            const res = await fetch(`/api/stars?limit=${limit}&offset=${offset}${q}`);
            if (!res.ok) throw new Error(`Failed to list stars: ${res.statusText}`);
            return await res.json();
        },
        async get(starId) {
            const res = await fetch(`/api/stars/${encodeURIComponent(starId)}`);
            if (!res.ok) throw new Error(`Failed to get star ${starId}: ${res.statusText}`);
            return await res.json();
        }
    },

    // 3. Single Star Analysis & Real-Time Job Tracking
    analysis: {
        async start(starId, forceRefresh = false, config = {}) {
            const res = await fetch("/api/analyze/star", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ star_id: starId, force_refresh: forceRefresh, config: config })
            });
            if (!res.ok) {
                const errData = await res.json().catch(() => ({}));
                throw new Error(errData.detail || `Failed to start analysis for ${starId}`);
            }
            return await res.json();
        },
        async getRun(runId) {
            const res = await fetch(`/api/runs/${encodeURIComponent(runId)}`);
            if (!res.ok) throw new Error(`Failed to get run status: ${res.statusText}`);
            return await res.json();
        },
        async getResults(runId) {
            const res = await fetch(`/api/results/${encodeURIComponent(runId)}`);
            if (!res.ok) throw new Error(`Failed to get run results: ${res.statusText}`);
            return await res.json();
        },
        async getLightcurve(starId) {
            const res = await fetch(`/api/lightcurve/${encodeURIComponent(starId)}`);
            if (!res.ok) {
                const errData = await res.json().catch(() => ({}));
                throw new Error(errData.detail || `Star ${starId} lightcurve failed to load.`);
            }
            return await res.json();
        }
    },

    // 4. Candidate Exploration & Filtering
    candidates: {
        async list({ minConfidence = 0.0, minSde = 0.0, status = "all", starId = "", sortBy = "confidence", order = "desc", limit = 50, offset = 0 } = {}) {
            const params = new URLSearchParams({
                min_confidence: minConfidence,
                min_sde: minSde,
                status: status,
                sort_by: sortBy,
                order: order,
                limit: limit,
                offset: offset
            });
            if (starId) params.append("star_id", starId);
            const res = await fetch(`/api/candidates?${params.toString()}`);
            if (!res.ok) throw new Error(`Failed to list candidates: ${res.statusText}`);
            return await res.json();
        },
        async get(candidateId) {
            const res = await fetch(`/api/candidates/${candidateId}`);
            if (!res.ok) throw new Error(`Failed to get candidate #${candidateId}: ${res.statusText}`);
            return await res.json();
        }
    },

    // 5. Arbitrary Light Curve Upload & Schema Detection
    data: {
        async upload(file) {
            const formData = new FormData();
            formData.append("file", file);
            const res = await fetch("/api/data/upload", {
                method: "POST",
                body: formData
            });
            if (!res.ok) {
                const errData = await res.json().catch(() => ({}));
                throw new Error(errData.detail || (errData.message ? `${errData.message}: ${errData.report?.errors?.join(", ") || ""}` : "Upload failed"));
            }
            return await res.json();
        }
    },

    // 6. Sky Journal Persistence
    journal: {
        async list(starId = "") {
            const q = starId ? `?star_id=${encodeURIComponent(starId)}` : "";
            const res = await fetch(`/api/journal${q}`);
            if (!res.ok) throw new Error(`Failed to fetch journal: ${res.statusText}`);
            return await res.json();
        },
        async create(entry) {
            const res = await fetch("/api/journal", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(entry)
            });
            if (!res.ok) throw new Error(`Failed to save journal entry: ${res.statusText}`);
            return await res.json();
        },
        async delete(entryId) {
            const res = await fetch(`/api/journal/${encodeURIComponent(entryId)}`, {
                method: "DELETE"
            });
            if (!res.ok) throw new Error(`Failed to delete journal entry: ${res.statusText}`);
            return await res.json();
        }
    },

    // 7. Batch Analysis & Official Submission
    batch: {
        async start(inputDir = "data/dev", workers = 4) {
            const res = await fetch(`/api/analyze/batch?input_dir=${encodeURIComponent(inputDir)}&workers=${workers}`, {
                method: "POST"
            });
            if (!res.ok) throw new Error(`Failed to start batch analysis: ${res.statusText}`);
            return await res.json();
        }
    },
    submission: {
        async generate(inputDir = "data/private_test") {
            const res = await fetch(`/api/submission?input_dir=${encodeURIComponent(inputDir)}`, {
                method: "POST"
            });
            if (!res.ok) {
                const errData = await res.json().catch(() => ({}));
                throw new Error(errData.detail || "Submission generation failed.");
            }
            return await res.json();
        },
        getDownloadUrl() {
            return "/api/submission/download";
        }
    },

    // 8. Sky Vision & Celestial Ephemerides
    sky: {
        async solve(imageBytesBase64, hintRa = null, hintDec = null, hintFov = null) {
            const res = await fetch("/api/sky/solve", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    image_base64: imageBytesBase64,
                    hint_ra: hintRa,
                    hint_dec: hintDec,
                    hint_fov: hintFov
                })
            });
            if (!res.ok) throw new Error(`Sky solve failed: ${res.statusText}`);
            return await res.json();
        },
        async getUniverse(lat = 11.0168, lon = 76.9558) {
            const res = await fetch(`/api/sky/universe?lat=${lat}&lon=${lon}`);
            if (!res.ok) throw new Error(`Failed to load universe: ${res.statusText}`);
            return await res.json();
        },
        async getPlanets(lat = 11.0168, lon = 76.9558) {
            const res = await fetch(`/api/sky/planets?lat=${lat}&lon=${lon}`);
            if (!res.ok) throw new Error(`Failed to fetch planets: ${res.statusText}`);
            return await res.json();
        }
    },

    // 9. ASTRA AI Scientific Assistant
    astra: {
        async chat({ message, starId = "", mode = "SCIENTIST", skyContext = null, sessionId = "default" }) {
            const res = await fetch("/api/assistant/chat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    message: message,
                    star_id: starId,
                    mode: mode,
                    sky_context: skyContext,
                    session_id: sessionId
                })
            });
            if (!res.ok) throw new Error(`CARL assistant error: ${res.statusText}`);
            return await res.json();
        }
    }
};

window.API = API;
