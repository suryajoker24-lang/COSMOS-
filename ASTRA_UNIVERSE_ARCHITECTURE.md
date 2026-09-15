# ASTRA UNIVERSE: System Architecture & Design Document

## 1. Overview & Vision

The platform unites celestial simulation and exoplanet detection into a cohesive architecture:
1. **ASTRA UNIVERSE**: Interactive 3D virtual planetarium and celestial sphere simulation with real astronomical coordinates, planetary ephemerides, constellations, and time-travel controls.
2. **ASTRA SCIENCE**: The Kepler long-cadence photometric transit detection and ML vetting engine.
3. **CARL**: The connective intelligence layer assisting across all domains with multi-persona explanations (Explore / Beginner / Scientist / Engineer).

---

## 2. Component Architecture

```
                       ┌─────────────────────────────────────┐
                       │                CARL                 │
                       │   Chat  •  Voice  •  Context State  │
                       └──────────────────┬──────────────────┘
                                          │
               ┌──────────────────────────┴──────────────────────────┐
               │                                                     │
      ┌────────▼─────────┐                                  ┌────────▼─────────┐
      │  ASTRA UNIVERSE  │                                  │  ASTRA SCIENCE   │
      │  3D Planetarium  │                                  │  Kepler Pipeline │
      ├──────────────────┤                                  ├──────────────────┤
      │ • Three.js WebGL │                                  │ • Quarter Norm   │
      │ • Stars & DSOs   │                                  │ • Adaptive SG    │
      │ • Constellations │                                  │ • Freq-Grid BLS  │
      │ • Ephemerides    │                                  │ • Vetting Suite  │
      │ • Time Travel    │                                  │ • LightGBM Model │
      │ • Location Sync  │                                  │ • Calibration    │
      └────────┬─────────┘                                  └────────┬─────────┘
               │                                                     │
               └──────────────────────────┬──────────────────────────┘
                                          │
                       ┌──────────────────▼──────────────────┐
                       │    Controlled Tools & Astrometry    │
                       │    Astropy • Ephemeris • Catalog    │
                       └─────────────────────────────────────┘
```

---

## 3. Data Flow & Integration Points

1. **Universe Observation Pipeline**:
   $$\text{Observer(Lat, Lon, UTC)} \xrightarrow{\text{Astropy / Ephemeris}} \text{Alt/Az, RA/Dec} \xrightarrow{\text{Three.js Dome}} \text{3D Celestial Sphere}$$
2. **CARL Context State**:
   Tracks active star, selected celestial body, observer location/time, and user persona level.
