# CARL: AI Scientific Astronomy Assistant

CARL is an intelligent astronomy assistant layered natively around the COSMOS Kepler Exoplanet Transit Detection System.

```
                 ┌──────────────────────────────────────┐
                 │          CARL AI ASSISTANT           │
                 │   Chat  •  Voice  •  Context Actions │
                 └──────────────────┬───────────────────┘
                                    │
                            Controlled Tools
                                    │
                ┌───────────────────┴───────────────────┐
                │                                       │
       Scientific Tool Layer                      Sky Tool Layer
                │                                       │
     ┌──────────▼──────────┐                 ┌──────────▼──────────┐
     │ KEPLER PHOTOMETRY   │                 │ SKY EXPLORER        │
     │ Light Curves        │                 │ Standard Catalog    │
     │ Adaptive Detrending │                 │ Astrometric Solver  │
     │ BLS Periodograms    │                 │ Constellations      │
     │ Vetting Diagnostics │                 │ Coordinates & FOV   │
     │ GroupKFold ML Model │                 │ Telescope (ASCOM)   │
     └─────────────────────┘                 └─────────────────────┘
```

---

## 1. Core Principles & Safety Model

1. **Zero Hallucination of Scientific Results**: Physical measurements (period, depth, duration, SNR, confidence, coordinates) are strictly read from the underlying scientific backend and allowlisted tools.
2. **Strict Tool Allowlisting**: CARL cannot execute arbitrary SQL queries, shell commands, or arbitrary Python scripts.
3. **Private Evaluation Truth Protection**: Private ground truth labels and test evaluation sets are automatically filtered and stripped by `AstraSafetyGuard`.
4. **Non-Destructive Integration**: The existing Kepler detection pipeline, scoring logic, model weights, and submission validation are untouched.

---

## 2. Explanation Personas

CARL dynamically adapts its explanations to three user levels:
- **BEGINNER**: Accessible, intuitive explanations with clear analogies (e.g. translating "ppm" to parts-per-million brightness drops and "BLS SDE" to signal distinctiveness).
- **SCIENTIST**: Rigorous astrophysical terminology quoting exact orbital periods (days), transit depths (ppm), durations (hours), and odd/even consistency significance ($\sigma$).
- **ENGINEER**: Detailed signal processing parameters, Savitzky-Golay detrending window sizes, quarter boundary gap handling, and LightGBM feature importances.

---

## 3. Allowlisted Controlled Tools

| Tool Name | Parameters | Description |
| :--- | :--- | :--- |
| `get_star_result` | `star_id` | Retrieves full scientific analysis, best candidate, and verdict for a star. |
| `get_lightcurve` | `star_id` | Retrieves observation baseline, cadence count, and noise parameters. |
| `get_candidates` | `star_id` | Returns all candidate peaks extracted from BLS periodogram. |
| `get_candidate_details` | `star_id`, `candidate_id` | Returns astrophysical vetting diagnostics and feature scores. |
| `get_validation_metrics` | None | Returns benchmark model performance on the development set. |
| `compare_candidates` | `star_id` | Compares top candidate peaks to identify true signals vs harmonics. |
| `explain_rejection` | `star_id` | Explains why a candidate or star was vetoed during vetting. |
| `get_model_information` | None | Returns LightGBM model configuration and feature importances. |
| `get_sky_object_info` | `object_name` | Queries astronomical catalog for stars, DSOs, or Kepler hosts. |

---

## 4. Sky Explorer & Astrophotographic Plate Solving

- **Viewport**: Interactive canvas rendering Cygnus / Lyra Kepler field stars, landmark anchors (Vega, Deneb, Albireo), deep sky objects (M42, M57, NGC 7000), and confirmed Kepler exoplanet host stars.
- **Plate Solving**: Local astrometric solver with star pattern matching returning RA, Dec, FOV, rotation, and identified catalog objects.
- **Telescope Protocol**: Abstracted ASCOM Alpaca / INDI integration requiring explicit user confirmation prior to any slew motor actuation.

---

## 5. Voice Interaction

- **Push-to-Talk**: Browser-native Web Speech API speech recognition or backend Whisper transcription.
- **Speech Synthesis**: Real-time spoken explanations via `window.speechSynthesis`.
