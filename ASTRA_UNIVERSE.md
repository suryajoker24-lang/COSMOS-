# ASTRA Universe: Interactive 3D Astronomical Sky & Space Simulation

## Overview
**ASTRA Universe** is an interactive, physically grounded 3D celestial sphere and space simulation engine integrated directly into the COSMOS Kepler Exoplanet Detection Platform. It transforms transit search and candidate vetting from abstract 1D curves into an immersive 3D astronomical journey suitable for beginners, space enthusiasts, and professional researchers.

---

## Key Features

### 1. WebGL 3D Celestial Sphere
- Rendered using **Three.js** on an inward-facing $R = 500\,\text{unit}$ celestial sphere.
- **Accurate Star Rendering**: 30 landmark stars with genuine $B-V$ color-index mappings (Harvard spectral types O, B, A, F, G, K, M) and magnitude-scaled radii.
- **Constellation Topologies**: Real-time rendering of constellation asterisms (Orion, Cygnus, Ursa Major, Cassiopeia, Lyra).
- **Deep-Sky Objects**: 3D spatial markers for M42 (Orion Nebula), M31 (Andromeda Galaxy), M45 (Pleiades), M57 (Ring Nebula), NGC 7000 (North America Nebula), and M13 (Great Hercules Cluster).
- **Kepler Survey Field**: Bounding perimeter highlighting the Kepler Primary Survey field in Cygnus/Lyra (centered at RA $295.5^\circ$, Dec $+44.5^\circ$).

### 2. Real-Time Solar System Ephemerides Engine
- Computes analytical Keplerian orbital elements and VSOP perturbation approximations for Sun, Moon, Mercury, Venus, Mars, Jupiter, Saturn (with rings!), Uranus, and Neptune.
- Horizon Coordinate Transformations: Converts equatorial coordinates $(\alpha, \delta)$ to observer-local Horizon coordinates $(\text{Alt}, \text{Az})$ for any given UTC timestamp and observer latitude/longitude.
- Real-time lunar phase illumination fractions (New Moon, Crescent, Quarter, Gibbous, Full Moon).

### 3. Time Travel & Orbital Mechanics Flow
- **Time Controls**:
  - Step backward/forward by 1 Hour (`-1h`, `+1h`)
  - Step backward/forward by 1 Day (`-1d`, `+1d`)
  - Live UTC / Tonight Anchor button
  - Continuous Time Flow Play/Pause animation engine with planetary spin and orbital motion.

### 4. Dual Experience Modes
- **Explore Mode**: Tailored for children, students, and amateur stargazers. Focuses on intuitive visual storytelling, planetary facts, constellations, and guided tours.
- **Scientist Mode**: Tailored for astrophysicists. Displays high-precision celestial coordinates, transit parameters ($P$, $\delta$, $\tau$), spectral types, distance moduli, and astrophysical candidate vetting metrics.

### 5. Guided Space Tours
- **Solar System Grand Tour**: Guides the user from the Sun through Mercury, Venus, Mars, Jupiter, and Saturn.
- **Habitable Zone Discoveries**: Tours confirmed habitable-zone systems (Kepler-186, Kepler-452, Kepler-22, Kepler-16).
- **Summer Triangle & Kepler Field**: Explores the Summer Triangle stars (Deneb, Vega, Altair) and the Kepler field.

### 6. Seamless Integrations
- **CARL**: Ask CARL to explain any selected celestial body, compare planetary systems, or provide astrophysical context.
- **Telescope Mount Interface**: Direct target slewing via ASCOM/INDI protocol simulations.

