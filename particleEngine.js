/**
 * COSMOS - 3D WebGL Particle System Core
 * High-performance GPU-instanced particle morphing engine
 * 4 States: 0=Cluster, 1=Eclipse, 2=Ring, 3=Glyph
 */

class CosmosParticleEngine {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        if (!this.container) {
            console.error(`Container #${containerId} not found`);
            return;
        }

        this.numParticles = 22000;
        this.clock = new THREE.Clock();
        this.mouse = { x: 0, y: 0, targetX: 0, targetY: 0 };
        this.morphProgress = 0.0; // 0.0 to 3.0
        this.targetMorphProgress = 0.0;
        this.cameraDolly = { z: 28, targetZ: 28, rotY: 0, targetRotY: 0 };

        this.init();
    }

    init() {
        const width = this.container.clientWidth || window.innerWidth;
        const height = this.container.clientHeight || window.innerHeight;

        // Scene
        this.scene = new THREE.Scene();

        // Camera
        this.camera = new THREE.PerspectiveCamera(55, width / height, 0.1, 1000);
        this.camera.position.set(0, 0, this.cameraDolly.z);

        // Renderer
        this.renderer = new THREE.WebGLRenderer({
            antialias: true,
            alpha: true,
            powerPreference: "high-performance"
        });
        this.renderer.setSize(width, height);
        this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
        this.renderer.setClearColor(0x000000, 0); // transparent background for CSS gradients
        this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
        this.renderer.toneMappingExposure = 0.92;
        this.container.appendChild(this.renderer.domElement);

        // Build Particle Geometry & Buffers
        this.createParticles();

        // Build Center Wireframe Glyph (appears in Ring state)
        this.createWireframeGlyph();

        // Events
        window.addEventListener("resize", this.onWindowResize.bind(this));
        window.addEventListener("mousemove", this.onMouseMove.bind(this));

        // Start render loop
        this.animate = this.animate.bind(this);
        requestAnimationFrame(this.animate);
    }

    createParticles() {
        const count = this.numParticles;
        const geometry = new THREE.BufferGeometry();

        const posCluster = new Float32Array(count * 3);
        const posEclipse = new Float32Array(count * 3);
        const posRing = new Float32Array(count * 3);
        const posGlyph = new Float32Array(count * 3);
        const randoms = new Float32Array(count);
        const sizes = new Float32Array(count);

        // 1. Cluster Target: Volumetric astronomical star cluster with soft falloff & text-safe offset
        for (let i = 0; i < count; i++) {
            const i3 = i * 3;
            // Smooth astronomical power distribution: prevents oversaturating central core
            const u = Math.random();
            const r = Math.pow(u, 1.25) * 14.5 + 0.8 + (Math.random() * 0.6);
            const theta = Math.random() * Math.PI * 2;
            const phi = Math.acos(2.0 * Math.random() - 1.0);

            // Shift cluster center downward to Y = -2.6 so it frames beneath the headline baseline
            posCluster[i3] = r * Math.sin(phi) * Math.cos(theta);
            posCluster[i3 + 1] = (r * Math.sin(phi) * Math.sin(theta)) * 0.82 - 2.6;
            posCluster[i3 + 2] = r * Math.cos(phi);

            randoms[i] = Math.random();
            // Delicate, crisp particle sizes (0.35 to 1.0)
            sizes[i] = 0.35 + Math.random() * 0.65;
        }

        // 2. Eclipse Target: Flat disk silhouette (dark core) + bright corona rim & rays
        for (let i = 0; i < count; i++) {
            const i3 = i * 3;
            const theta = Math.random() * Math.PI * 2;
            let r, z;

            if (i < count * 0.75) {
                // Dense glowing corona rim: radius 5.6 to 8.2
                const rimSpread = Math.pow(Math.random(), 2.0);
                r = 5.6 + rimSpread * 2.8;
                z = (Math.random() - 0.5) * 1.2;
            } else {
                // Outward corona streamers & solar wind
                const streamDist = Math.pow(Math.random(), 1.5);
                r = 8.4 + streamDist * 12.0;
                z = (Math.random() - 0.5) * 2.8;
            }

            // Eclipse starts slightly off-center (-2.5 in X) then re-centers
            posEclipse[i3] = r * Math.cos(theta) - 1.2;
            posEclipse[i3 + 1] = r * Math.sin(theta) * 0.95;
            posEclipse[i3 + 2] = z;
        }

        // 3. Ring Target: Thin orbital torus / Keplerian accretion disc
        for (let i = 0; i < count; i++) {
            const i3 = i * 3;
            const theta = Math.random() * Math.PI * 2;

            if (i < count * 0.88) {
                // Torus ring: radius around 9.8
                const ringWidth = (Math.random() - 0.5) * 2.2;
                const r = 9.8 + ringWidth;
                posRing[i3] = r * Math.cos(theta);
                posRing[i3 + 1] = (r * Math.sin(theta)) * 0.45; // angled tilt
                posRing[i3 + 2] = (Math.random() - 0.5) * 0.8 + (r * Math.sin(theta)) * 0.6;
            } else {
                // Micro inner-core halo surrounding the central wireframe glyph
                const r = Math.pow(Math.random(), 2) * 2.2;
                posRing[i3] = r * Math.cos(theta);
                posRing[i3 + 1] = r * Math.sin(theta);
                posRing[i3 + 2] = (Math.random() - 0.5) * 1.2;
            }
        }

        // 4. Glyph Target: Brand Mark - COSMOS Kepler Satellite & Exoplanet Transit Silhouette
        // Sampled along concentric orbital curves, central planet disk, and transit chevron
        for (let i = 0; i < count; i++) {
            const i3 = i * 3;
            const fraction = i / count;
            let gx = 0, gy = 0, gz = 0;

            if (fraction < 0.35) {
                // Outer orbital ellipse arc
                const angle = (i / (count * 0.35)) * Math.PI * 2;
                const rx = 10.5 + (Math.random() - 0.5) * 0.35;
                const ry = 4.8 + (Math.random() - 0.5) * 0.35;
                gx = rx * Math.cos(angle);
                gy = ry * Math.sin(angle) * 0.9 + gx * 0.22;
                gz = (Math.random() - 0.5) * 0.6;
            } else if (fraction < 0.65) {
                // Central Exoplanet Transit Disk
                const angle = Math.random() * Math.PI * 2;
                const r = Math.sqrt(Math.random()) * 3.4;
                gx = r * Math.cos(angle);
                gy = r * Math.sin(angle);
                gz = (Math.random() - 0.5) * 0.5;
            } else if (fraction < 0.82) {
                // Horizontal transit light curve chord
                const t = ((i - count * 0.65) / (count * 0.17)) * 2.0 - 1.0;
                gx = t * 11.5;
                // Gaussian dip in the center simulating transit light curve
                gy = -1.2 * Math.exp(-gx * gx * 0.35) + (Math.random() - 0.5) * 0.2;
                gz = (Math.random() - 0.5) * 0.4;
            } else {
                // Kepler Sensor Chevron / Aperture Triangle
                const t = Math.random();
                const side = Math.floor(Math.random() * 3);
                const p0 = [-5.0, 5.0], p1 = [5.0, 5.0], p2 = [0.0, 8.5];
                let px, py;
                if (side === 0) {
                    px = p0[0] + (p1[0] - p0[0]) * t;
                    py = p0[1] + (p1[1] - p0[1]) * t;
                } else if (side === 1) {
                    px = p1[0] + (p2[0] - p1[0]) * t;
                    py = p1[1] + (p2[1] - p1[1]) * t;
                } else {
                    px = p2[0] + (p0[0] - p2[0]) * t;
                    py = p2[1] + (p0[1] - p2[1]) * t;
                }
                gx = px + (Math.random() - 0.5) * 0.3;
                gy = py - 4.0 + (Math.random() - 0.5) * 0.3;
                gz = (Math.random() - 0.5) * 0.5;
            }

            posGlyph[i3] = gx;
            posGlyph[i3 + 1] = gy;
            posGlyph[i3 + 2] = gz;
        }

        // Attach attributes
        geometry.setAttribute("position", new THREE.BufferAttribute(posCluster, 3));
        geometry.setAttribute("aPosCluster", new THREE.BufferAttribute(posCluster, 3));
        geometry.setAttribute("aPosEclipse", new THREE.BufferAttribute(posEclipse, 3));
        geometry.setAttribute("aPosRing", new THREE.BufferAttribute(posRing, 3));
        geometry.setAttribute("aPosGlyph", new THREE.BufferAttribute(posGlyph, 3));
        geometry.setAttribute("aRandom", new THREE.BufferAttribute(randoms, 1));
        geometry.setAttribute("aSize", new THREE.BufferAttribute(sizes, 1));

        // Custom GLSL Shaders
        const vertexShader = `
            attribute vec3 aPosCluster;
            attribute vec3 aPosEclipse;
            attribute vec3 aPosRing;
            attribute vec3 aPosGlyph;
            attribute float aRandom;
            attribute float aSize;

            uniform float uTime;
            uniform float uMorphProgress; // 0.0 -> 3.0
            uniform float uPixelRatio;
            uniform vec2 uMouseParallax;

            varying float vHeat;
            varying float vAlpha;

            // Pseudo curl noise for idle breathing
            vec3 getCurl(vec3 p) {
                float t = uTime * 0.22;
                return vec3(
                    sin(p.y * 0.4 + t) * cos(p.z * 0.3 + t * 0.6),
                    sin(p.z * 0.4 + t * 0.7) * cos(p.x * 0.3 + t * 0.5),
                    sin(p.x * 0.4 + t * 0.8) * cos(p.y * 0.3 + t * 0.4)
                );
            }

            void main() {
                float p = clamp(uMorphProgress, 0.0, 3.0);
                vec3 targetPos;

                if (p <= 1.0) {
                    float t = smoothstep(0.0, 1.0, p);
                    targetPos = mix(aPosCluster, aPosEclipse, t);
                } else if (p <= 2.0) {
                    float t = smoothstep(0.0, 1.0, p - 1.0);
                    targetPos = mix(aPosEclipse, aPosRing, t);
                } else {
                    float t = smoothstep(0.0, 1.0, p - 2.0);
                    targetPos = mix(aPosRing, aPosGlyph, t);
                }

                // Gentle curl noise idle drift
                vec3 drift = getCurl(targetPos * 0.2 + vec3(aRandom * 8.0)) * 0.65;
                vec3 finalPos = targetPos + drift;

                // Subtle cursor parallax
                finalPos.x += uMouseParallax.x * (1.2 + aRandom * 0.8);
                finalPos.y += uMouseParallax.y * (1.2 + aRandom * 0.8);

                vec4 mvPosition = modelViewMatrix * vec4(finalPos, 1.0);
                gl_Position = projectionMatrix * mvPosition;

                // Size attenuation: delicate, sharp points that preserve individual texture
                float dist = -mvPosition.z;
                float baseSize = aSize * (150.0 / max(dist, 1.0)) * uPixelRatio;
                gl_PointSize = clamp(baseSize, 1.0, 15.0);

                // Heat: smooth natural Gaussian falloff centered below headline
                float rad = length(finalPos - vec3(0.0, -2.6, 0.0));
                float coreWeight = clamp(1.0 - (rad / 11.0), 0.0, 1.0);
                vHeat = pow(coreWeight, 1.6) * (0.65 + 0.35 * sin(uTime * 1.5 + aRandom * 6.28));
                vAlpha = clamp(1.0 - (dist / 95.0), 0.2, 0.95);
            }
        `;

        const fragmentShader = `
            uniform vec3 uCoreColor;
            uniform vec3 uEdgeColor;
            uniform vec3 uAccentColor;

            varying float vHeat;
            varying float vAlpha;

            void main() {
                vec2 coord = gl_PointCoord - vec2(0.5);
                float distSq = dot(coord, coord);
                if (distSq > 0.25) discard;

                // Smooth Gaussian point profile
                float radial = exp(-distSq * 14.0);

                // Color ramp: electric blue (#7C9CFF) to bright core
                // Clamped so it never clips to a solid flat disc
                vec3 col = mix(uEdgeColor, uCoreColor, clamp(pow(vHeat, 1.8), 0.0, 0.88));
                if (vHeat > 0.72) {
                    col = mix(col, vec3(1.0, 1.0, 1.0), (vHeat - 0.72) * 1.1);
                }

                // Delicate alpha so overlapping points sparkle rather than blow out
                float finalAlpha = radial * vAlpha * 0.58;

                gl_FragColor = vec4(col, finalAlpha);
            }
        `;

        this.uniforms = {
            uTime: { value: 0.0 },
            uMorphProgress: { value: 0.0 },
            uPixelRatio: { value: Math.min(window.devicePixelRatio || 1, 2) },
            uMouseParallax: { value: new THREE.Vector2(0, 0) },
            uCoreColor: { value: new THREE.Color("#FFFFFF") },
            uEdgeColor: { value: new THREE.Color("#7C9CFF") },
            uAccentColor: { value: new THREE.Color("#3B82F6") }
        };

        const material = new THREE.ShaderMaterial({
            vertexShader: vertexShader,
            fragmentShader: fragmentShader,
            uniforms: this.uniforms,
            transparent: true,
            blending: THREE.AdditiveBlending,
            depthWrite: false
        });

        this.particleSystem = new THREE.Points(geometry, material);
        this.scene.add(this.particleSystem);
    }

    createWireframeGlyph() {
        // Subtle wireframe glyph at center (visible when in state 2: Ring)
        const group = new THREE.Group();

        const ringGeom = new THREE.TorusGeometry(1.6, 0.03, 16, 64);
        const ringMat = new THREE.MeshBasicMaterial({
            color: 0x7C9CFF,
            wireframe: true,
            transparent: true,
            opacity: 0.0
        });
        this.wireframeRing = new THREE.Mesh(ringGeom, ringMat);
        group.add(this.wireframeRing);

        const coreGeom = new THREE.IcosahedronGeometry(0.85, 1);
        const coreMat = new THREE.MeshBasicMaterial({
            color: 0xFFFFFF,
            wireframe: true,
            transparent: true,
            opacity: 0.0
        });
        this.wireframeCore = new THREE.Mesh(coreGeom, coreMat);
        group.add(this.wireframeCore);

        this.glyphGroup = group;
        this.scene.add(this.glyphGroup);
    }

    setMorphProgress(value) {
        this.targetMorphProgress = Math.max(0.0, Math.min(3.0, value));
    }

    setCameraDolly(z, rotY) {
        if (z !== undefined) this.cameraDolly.targetZ = z;
        if (rotY !== undefined) this.cameraDolly.targetRotY = rotY;
    }

    onMouseMove(e) {
        const nx = (e.clientX / window.innerWidth) * 2 - 1;
        const ny = -(e.clientY / window.innerHeight) * 2 + 1;
        this.mouse.targetX = nx * 1.5;
        this.mouse.targetY = ny * 1.5;
    }

    onWindowResize() {
        if (!this.container || !this.renderer || !this.camera) return;
        const width = this.container.clientWidth || window.innerWidth;
        const height = this.container.clientHeight || window.innerHeight;

        this.camera.aspect = width / height;
        this.camera.updateProjectionMatrix();

        this.renderer.setSize(width, height);
        this.uniforms.uPixelRatio.value = Math.min(window.devicePixelRatio || 1, 2);
    }

    animate() {
        requestAnimationFrame(this.animate);

        const delta = this.clock.getDelta();
        const elapsed = this.clock.getElapsedTime();

        // Smooth lerp morphProgress
        this.morphProgress += (this.targetMorphProgress - this.morphProgress) * 0.08;
        this.uniforms.uMorphProgress.value = this.morphProgress;
        this.uniforms.uTime.value = elapsed;

        // Smooth lerp mouse parallax
        this.mouse.x += (this.mouse.targetX - this.mouse.x) * 0.06;
        this.mouse.y += (this.mouse.targetY - this.mouse.y) * 0.06;
        this.uniforms.uMouseParallax.value.set(this.mouse.x, this.mouse.y);

        // Smooth camera dolly
        this.cameraDolly.z += (this.cameraDolly.targetZ - this.cameraDolly.z) * 0.07;
        this.cameraDolly.rotY += (this.cameraDolly.targetRotY - this.cameraDolly.rotY) * 0.05;

        this.camera.position.z = this.cameraDolly.z;
        this.camera.rotation.y = this.cameraDolly.rotY + this.mouse.x * 0.03;
        this.camera.rotation.x = -this.mouse.y * 0.03;

        // Animate central wireframe glyph (fades in during Ring state around morph=2.0)
        if (this.glyphGroup) {
            this.glyphGroup.rotation.y = elapsed * 0.45;
            this.glyphGroup.rotation.x = elapsed * 0.25;

            // Opacity peaks when morphProgress is between 1.7 and 2.3
            const ringProximity = Math.max(0, 1.0 - Math.abs(this.morphProgress - 2.0) * 2.5);
            this.wireframeRing.material.opacity = ringProximity * 0.65;
            this.wireframeCore.material.opacity = ringProximity * 0.85;
        }

        // Particle system global subtle orbit
        if (this.particleSystem) {
            this.particleSystem.rotation.y = elapsed * 0.035;
        }

        this.renderer.render(this.scene, this.camera);
    }
}

window.CosmosParticleEngine = CosmosParticleEngine;
