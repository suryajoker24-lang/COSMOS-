# CARL Context Engine & UI Integration

## Overview
The **CARL Context Engine** maintains bidirectional synchronization between the user's active UI view (Single Star Analyzer or 3D Universe) and the CARL AI reasoning model.

---

## 1. Context State Lifecycle

```
   ┌────────────────────────────────────────────────────────┐
   │                   CARL Context State                   │
   │                                                        │
   │  • Current Star: STAR_0001 (P=82.5d, Depth=450ppm)    │
   │  • Active 3D Body: Kepler-186 (RA=298.65°, Dec=44.62°) │
   │  • User Experience Mode: SCIENTIST / BEGINNER          │
   │  • Active Target: Cygnus / Kepler Field                │
   └────────────────────────────────────────────────────────┘
                               ▲
                               │
            ┌──────────────────┴──────────────────┐
            ▼                                     ▼
 [FastAPI Backend Engine]              [Interactive Web UI]
  • Tool Registry Evaluation            • Three.js 3D Viewport Slew
  • Safe Parameter Extraction           • Target Selection
  • Astrophysical Explanations          • Light Curve Highlighting
```

---

## 2. Visual Actions Routing
When CARL generates answers, it can emit structured `VisualAction` commands executed in real-time by the frontend:
- `center_sky_coordinates`: Slews 3D planetarium camera to $(\text{RA}, \text{Dec})$.
- `show_constellation`: Highlights constellation asterism lines.
- `open_star`: Loads Kepler light curve in the Single Star Analyzer.
- `highlight_candidate`: Zooms phase-folded chart onto the detected transit epoch.

---

## 3. Safety & Ground-Truth Isolation
- User input is sanitized against injection attacks before passing to LLM prompts.
- Private evaluation test labels and benchmark ground truths are isolated by `safety_guard.protect_private_truth()`.
- Dangerous mount slewing actions require explicit user confirmation before executing ASCOM/INDI commands.

