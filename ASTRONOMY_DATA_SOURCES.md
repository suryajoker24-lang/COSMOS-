# Astronomical Catalogs & Ephemeris Data Sources

## Overview
ASTRA aggregates peer-reviewed astronomical catalogs, physical planetary orbital data, and Kepler space mission data to provide grounded celestial positions and astrophysical parameters.

---

## 1. Solar System Ephemerides (VSOP87 Analytical Theory)
- Planetary positions are evaluated using analytical Keplerian orbital elements with secular drift rates referenced to the J2000.0 epoch ($JD = 2451545.0$).
- **Planets Modeled**: Mercury, Venus, Earth-Moon barycenter, Mars, Jupiter, Saturn (with rings), Uranus, Neptune.
- **Lunar Ephemeris**: Computes geocentric ecliptic longitude/latitude, synodic phase angle, and illumination percentage ($0\text{--}100\%$).

---

## 2. Landmark Visible Stars & Color Temperatures
- **Catalogs**: Bright Star Catalog (Yale), Hipparcos / Gaia DR3 photometric standards.
- **Spectral Classification**: Harvard spectral sequence (O, B, A, F, G, K, M) mapped through the color index $B-V$:
  - $B-V < 0.0$: Blue ($\approx 30,000\,\text{K}$)
  - $0.0 \le B-V < 0.3$: Blue-White ($\approx 10,000\,\text{K}$)
  - $0.3 \le B-V < 0.6$: White ($\approx 7,500\,\text{K}$)
  - $0.6 \le B-V < 0.8$: Yellow-White / Sun-like ($\approx 5,800\,\text{K}$)
  - $0.8 \le B-V < 1.4$: Orange Giant ($\approx 4,200\,\text{K}$)
  - $B-V \ge 1.4$: Red Dwarf / Red Supergiant ($\approx 3,000\,\text{K}$)

---

## 3. Kepler Mission DR25 Catalog
- Ground-truth and validated exoplanet parameters sourced from the NASA Exoplanet Archive Kepler Q1-Q17 DR25 KOI catalog.
- Reference landmark host stars include **Kepler-186** (habitable-zone Earth analog), **Kepler-452** (Sun-like host), **Kepler-22** (first transiting HZ super-Earth), and **Kepler-16** (Tatooine-like circumbinary system).

---

## 4. Deep-Sky Objects (Messier & New General Catalogue)
- Includes planetary nebulae, emission nebulae, open clusters, globular clusters, and spiral galaxies (M42 Orion Nebula, M31 Andromeda Galaxy, M45 Pleiades, M57 Ring Nebula, NGC 7000 North America Nebula, M13 Great Hercules Cluster).

