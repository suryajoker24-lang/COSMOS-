# ASTRA Plate Solving & Astrometric Calibration Engine

## Overview
Plate solving (blind astrometric calibration) is the mathematical process of determining the exact pointing direction $(\alpha, \delta)$, pixel scale ($s$ arcsec/pixel), and celestial orientation angle ($\theta$) of an arbitrary astronomical image without prior pointing knowledge.

---

## Mathematical Formulation

### 1. Geometric Star Triangle Hashing
Given $N \ge 3$ detected stellar centroids $\{p_1, p_2, \dots, p_N\}$ in 2D image coordinates $(x_i, y_i)$, ASTRA forms triplet combinations $(p_a, p_b, p_c)$ with sides $L_{12}, L_{23}, L_{31}$ ordered such that $L_{12} \le L_{23} \le L_{31}$.

The scale-invariant and rotation-invariant shape descriptor vector is given by:
$$\mathbf{h} = \left( \frac{L_{12}}{L_{31}}, \frac{L_{23}}{L_{31}} \right) \in (0, 1]^2$$

This $2\text{D}$ invariant hash is looked up in a $k\text{-d}$ tree of catalog asterism hashes computed from SIMBAD/Gaia DR3 reference landmarks.

### 2. World Coordinate System (WCS) Transformation
The mapping between $(x, y)$ pixel coordinates and tangent plane coordinates $(\xi, \eta)$ is modeled via a standard affine transformation:
$$\begin{pmatrix} \xi \\ \eta \end{pmatrix} = \begin{pmatrix} \text{CD}_{11} & \text{CD}_{12} \\ \text{CD}_{21} & \text{CD}_{22} \end{pmatrix} \begin{pmatrix} x - x_0 \\ y - y_0 \end{pmatrix}$$

where $(x_0, y_0)$ is the optical center (CRPIX) and $\text{CD}_{ij}$ is the coordinate description matrix encoding field rotation and pixel scale.

The celestial coordinates $(\alpha, \delta)$ are derived via the GNOMONIC projection:
$$\alpha = \alpha_0 + \arctan\left(\frac{\xi}{\cos \delta_0 - \eta \sin \delta_0}\right)$$
$$\delta = \arcsin\left(\frac{\sin \delta_0 + \eta \cos \delta_0}{\sqrt{1 + \xi^2 + \eta^2}}\right)$$

### 3. Confidence Metric & Quality Gating
The match confidence is derived from the root-mean-square positional residual $\sigma_{\text{RMS}}$ of matched catalog stars:
$$\sigma_{\text{RMS}} = \sqrt{\frac{1}{M} \sum_{k=1}^M \Delta \theta_k^2}$$
$$\text{Confidence} = \max\left(0, 1 - \frac{\sigma_{\text{RMS}}}{0.10^\circ}\right) \times 100\%$$

If $\sigma_{\text{RMS}} > 0.15^\circ$ or $M < 4$, the solution is safely flagged as unverified to prevent false identifications.

