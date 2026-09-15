/**
 * COSMOS Interactive Landing Page - Master Scroll Choreography & UI
 * Powered by Lenis smooth scroll, GSAP ScrollTrigger, and CosmosParticleEngine
 */

document.addEventListener("DOMContentLoaded", () => {
    // 1. Check for reduced motion preference
    const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    // 2. Initialize Particle Engine
    const particleEngine = new CosmosParticleEngine("webglContainer");

    // 3. Preloader Hyperspace Streak Animation & Counter
    initPreloader(() => {
        // Preloader complete callback: initialize scroll timeline & kinetic text
        initLandingExperience(particleEngine, prefersReducedMotion);
    });

    // 4. Cursor Radial Glow Hotspot
    initCursorGlow();

    // 5. Contact Micro-Form Handler
    initContactForm();
});

/**
 * Preloader Hyperspace Warp Streaks & Technical Counter
 */
function initPreloader(onComplete) {
    const preloaderEl = document.getElementById("preloader");
    const canvas = document.getElementById("preloaderCanvas");
    const percentEl = document.getElementById("preloaderPercent");
    const barEl = document.getElementById("preloaderBar");
    const statusTextEl = document.getElementById("preloaderStatusText");

    if (!preloaderEl || !canvas) {
        if (onComplete) onComplete();
        return;
    }

    const ctx = canvas.getContext("2d");
    let width = (canvas.width = window.innerWidth);
    let height = (canvas.height = window.innerHeight);

    window.addEventListener("resize", () => {
        width = canvas.width = window.innerWidth;
        height = canvas.height = window.innerHeight;
    });

    // 220 warp star streaks
    const stars = [];
    const numStars = 220;
    for (let i = 0; i < numStars; i++) {
        stars.push({
            x: (Math.random() - 0.5) * width,
            y: (Math.random() - 0.5) * height,
            z: Math.random() * width,
            pz: Math.random() * width,
            speed: 18 + Math.random() * 24
        });
    }

    let progress = 0;
    const targetProgress = 100;
    let animRunning = true;

    const statusMessages = [
        "CALIBRATING KEPLER CCD SENSORS...",
        "INDEXING 17-QUARTER SAP PHOTOMETRY...",
        "COMPUTING 22,000 GPU MORPH MATRICES...",
        "SYNCHRONIZING MASTER SCROLL TIMELINE...",
        "GRAVITATIONAL CLUSTER LOCKED // 100%"
    ];

    function drawWarp() {
        if (!animRunning) return;
        requestAnimationFrame(drawWarp);

        ctx.fillStyle = "rgba(5, 7, 12, 0.28)";
        ctx.fillRect(0, 0, width, height);

        const cx = width / 2;
        const cy = height / 2;

        for (let i = 0; i < numStars; i++) {
            const s = stars[i];
            s.z -= s.speed;
            if (s.z <= 0) {
                s.z = width;
                s.pz = width;
                s.x = (Math.random() - 0.5) * width;
                s.y = (Math.random() - 0.5) * height;
            }

            const k = 250 / s.z;
            const px = s.x * k + cx;
            const py = s.y * k + cy;

            const pk = 250 / s.pz;
            const prevX = s.x * pk + cx;
            const prevY = s.y * pk + cy;
            s.pz = s.z;

            // Draw streak
            ctx.beginPath();
            ctx.moveTo(prevX, prevY);
            ctx.lineTo(px, py);
            const alpha = Math.min(1.0, (1.0 - s.z / width) * 1.5);
            ctx.strokeStyle = `rgba(124, 156, 255, ${alpha})`;
            ctx.lineWidth = Math.max(0.6, (1.0 - s.z / width) * 2.2);
            ctx.stroke();
        }

        // Progress counter progression
        if (progress < targetProgress) {
            progress += (targetProgress - progress) * 0.045 + 0.35;
            if (progress > targetProgress) progress = targetProgress;

            const displayVal = Math.floor(progress);
            if (percentEl) percentEl.textContent = `${displayVal}%`;
            if (barEl) barEl.style.width = `${displayVal}%`;

            const msgIdx = Math.min(
                statusMessages.length - 1,
                Math.floor((displayVal / 100) * statusMessages.length)
            );
            if (statusTextEl) statusTextEl.textContent = statusMessages[msgIdx];
        } else {
            // Finished preloader
            animRunning = false;
            gsap.to(preloaderEl, {
                opacity: 0,
                scale: 1.05,
                duration: 0.9,
                ease: "power2.inOut",
                onComplete: () => {
                    preloaderEl.style.display = "none";
                    if (onComplete) onComplete();
                }
            });
        }
    }

    requestAnimationFrame(drawWarp);
}

/**
 * Initialize Lenis Smooth Scroll & GSAP ScrollTrigger Master Timeline
 */
function initLandingExperience(particleEngine, prefersReducedMotion) {
    // 1. Lenis Smooth Scroll
    let lenis = null;
    if (!prefersReducedMotion && typeof Lenis !== "undefined") {
        lenis = new Lenis({
            duration: 1.25,
            easing: (t) => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
            direction: "vertical",
            smooth: true
        });

        function raf(time) {
            lenis.raf(time);
            requestAnimationFrame(raf);
        }
        requestAnimationFrame(raf);

        // Connect Lenis to ScrollTrigger
        lenis.on("scroll", ScrollTrigger.update);
        gsap.ticker.add((time) => {
            lenis.raf(time * 1000);
        });
        gsap.ticker.lagSmoothing(0);
    }

    // Register GSAP Plugins
    if (typeof gsap !== "undefined" && typeof ScrollTrigger !== "undefined") {
        gsap.registerPlugin(ScrollTrigger);
    }

    // Animate Hero Text Entrance on load
    animateHeroEntrance();

    if (prefersReducedMotion) {
        // Fallback for reduced motion: simple static values
        particleEngine.setMorphProgress(0);
        return;
    }

    // 2. Master Scroll-Scrubbed Timeline
    // Driven across the whole page height (sections 01 through 04)
    const masterTimeline = gsap.timeline({
        scrollTrigger: {
            trigger: "#scrollWrapper",
            start: "top top",
            end: "bottom bottom",
            scrub: 1.2,
            onUpdate: (self) => {
                const progress = self.progress; // 0.0 to 1.0
                // Map progress (0 -> 1) to particle morphProgress (0.0 -> 3.0)
                const morph = progress * 3.0;
                particleEngine.setMorphProgress(morph);

                // Dynamically adjust camera dolly & tilt
                if (morph < 1.0) {
                    // Cluster state: deep camera view
                    particleEngine.setCameraDolly(28 - morph * 5, morph * 0.15);
                } else if (morph < 2.0) {
                    // Eclipse state: closer view with dramatic tilt
                    const localM = morph - 1.0;
                    particleEngine.setCameraDolly(23 - localM * 3, 0.15 - localM * 0.45);
                } else {
                    // Ring to Glyph state: pulled back to showcase full brand mark
                    const localM = morph - 2.0;
                    particleEngine.setCameraDolly(20 + localM * 7, -0.3 + localM * 0.3);
                }
            }
        }
    });

    // 3. Strict Mutually Exclusive Headline State Management (Fixes headline overlap)
    setupHeadlineStateManagement();

    // 4. Section 2 (Eclipse) Kinetic Typography Word Reveal
    setupStatementWordReveal();

    // 5. Section 3 (Process Rail) Timeline & Sliding Triangle Marker
    setupProcessRailTimeline();

    // 6. Hero Pillar Rails Hairline Underlines
    setupPillarHairlines();

    // 7. Section 4 (Convergence / CTA) Entrance
    setupConvergenceEntrance();
}

/**
 * Strict Mutually Exclusive Headline State Machine
 * Guarantees that at any given scroll position, EXACTLY ONE headline is active.
 */
function setupHeadlineStateManagement() {
    const h1 = document.getElementById("headline-block-1");
    const h2 = document.getElementById("headline-block-2");
    const h3 = document.getElementById("headline-block-3");
    if (!h1 || !h2) return;

    // Strict initial mount states
    gsap.set(h1, { opacity: 1, visibility: "visible", pointerEvents: "auto", y: 0 });
    gsap.set(h2, { opacity: 0, visibility: "hidden", pointerEvents: "none", y: 20 });
    if (h3) gsap.set(h3, { opacity: 0, visibility: "hidden", pointerEvents: "none", y: 25 });

    // ScrollTrigger for Hero Headline Swap (h1 -> h2)
    ScrollTrigger.create({
        trigger: "#section-hero",
        start: "top top",
        end: "bottom 15%",
        scrub: 0.5,
        onUpdate: (self) => {
            const p = self.progress; // 0.0 to 1.0

            if (p < 0.30) {
                // Phase A: Headline 1 active
                const fade = Math.max(0, Math.min(1, (0.30 - p) / 0.12));
                h1.style.opacity = Math.min(1, 0.15 + fade * 0.85);
                h1.style.visibility = "visible";
                h1.style.pointerEvents = "auto";
                h1.style.transform = `translateY(${-(1 - fade) * 15}px)`;

                h2.style.opacity = "0";
                h2.style.visibility = "hidden";
                h2.style.pointerEvents = "none";
            } else if (p >= 0.30 && p < 0.46) {
                // Dead Zone Gap: Headline 1 fades out completely BEFORE Headline 2 enters
                const fadeOut = Math.max(0, (0.40 - p) / 0.10);
                h1.style.opacity = fadeOut;
                h1.style.transform = `translateY(${-(1 - fadeOut) * 20}px)`;
                if (fadeOut <= 0.02) {
                    h1.style.visibility = "hidden";
                    h1.style.pointerEvents = "none";
                }

                h2.style.opacity = "0";
                h2.style.visibility = "hidden";
                h2.style.pointerEvents = "none";
            } else if (p >= 0.46 && p < 0.80) {
                // Phase B: Headline 2 enters and stays active
                h1.style.opacity = "0";
                h1.style.visibility = "hidden";
                h1.style.pointerEvents = "none";

                const fadeIn = Math.min(1, (p - 0.46) / 0.12);
                h2.style.visibility = "visible";
                h2.style.pointerEvents = "auto";
                h2.style.opacity = fadeIn;
                h2.style.transform = `translateY(${(1 - fadeIn) * 18}px)`;
            } else {
                // Phase C: Headline 2 fades out before Statement section arrives
                h1.style.opacity = "0";
                h1.style.visibility = "hidden";
                h1.style.pointerEvents = "none";

                const fadeOut2 = Math.max(0, (0.95 - p) / 0.15);
                h2.style.opacity = fadeOut2;
                h2.style.transform = `translateY(${-(1 - fadeOut2) * 20}px)`;
                if (fadeOut2 <= 0.02) {
                    h2.style.visibility = "hidden";
                    h2.style.pointerEvents = "none";
                }
            }
        }
    });

    // ScrollTrigger for Section 2 (Statement)
    if (h3) {
        ScrollTrigger.create({
            trigger: "#section-statement",
            start: "top 65%",
            end: "bottom 35%",
            onEnter: () => {
                gsap.to(h3, { opacity: 1, visibility: "visible", pointerEvents: "auto", y: 0, duration: 0.6, ease: "power2.out" });
            },
            onLeave: () => {
                gsap.to(h3, { opacity: 0, duration: 0.4, ease: "power2.in", onComplete: () => {
                    h3.style.visibility = "hidden";
                    h3.style.pointerEvents = "none";
                }});
            },
            onEnterBack: () => {
                h3.style.visibility = "visible";
                h3.style.pointerEvents = "auto";
                gsap.to(h3, { opacity: 1, y: 0, duration: 0.6, ease: "power2.out" });
            },
            onLeaveBack: () => {
                gsap.to(h3, { opacity: 0, duration: 0.4, ease: "power2.in", onComplete: () => {
                    h3.style.visibility = "hidden";
                    h3.style.pointerEvents = "none";
                }});
            }
        });
    }
}

/**
 * Hero Initial Kinetic Entrance
 */
function animateHeroEntrance() {
    gsap.from("#heroBadge", {
        opacity: 0,
        y: -15,
        duration: 0.8,
        delay: 0.2,
        ease: "power3.out"
    });

    gsap.from("#headline-block-1 .hero-headline-word", {
        opacity: 0,
        y: 35,
        filter: "blur(10px)",
        stagger: 0.055,
        duration: 1.1,
        delay: 0.35,
        ease: "power3.out"
    });

    gsap.from("#heroSubtext", {
        opacity: 0,
        y: 20,
        duration: 0.9,
        delay: 0.8,
        ease: "power3.out"
    });

    gsap.from(".pillar-card", {
        opacity: 0,
        x: (i) => (i % 2 === 0 ? -30 : 30),
        duration: 0.9,
        stagger: 0.12,
        delay: 0.9,
        ease: "power3.out",
        onComplete: () => {
            // Fill initial hero pillar hairlines
            document.querySelectorAll(".pillar-hairline-fill").forEach((el) => {
                el.style.width = "100%";
            });
        }
    });
}

/**
 * Statement Section: Word-by-word reveal with blur & opacity stagger
 */
function setupStatementWordReveal() {
    const words = document.querySelectorAll(".statement-word");
    if (!words.length) return;

    gsap.set(words, { opacity: 0.15, filter: "blur(6px)", y: 15 });

    ScrollTrigger.create({
        trigger: "#section-statement",
        start: "top 75%",
        end: "center 45%",
        scrub: 1.0,
        onUpdate: (self) => {
            const p = self.progress;
            const totalWords = words.length;
            words.forEach((word, idx) => {
                const wordStart = idx / totalWords;
                const wordProgress = Math.max(0, Math.min(1, (p - wordStart) * totalWords * 1.5));
                const opacity = 0.15 + wordProgress * 0.85;
                const blur = (1 - wordProgress) * 6;
                const y = (1 - wordProgress) * 15;

                word.style.opacity = opacity;
                word.style.filter = `blur(${blur}px)`;
                word.style.transform = `translateY(${y}px)`;
            });
        }
    });
}

/**
 * Process Timeline 01-05 Rail with Sliding Triangle Marker
 */
function setupProcessRailTimeline() {
    const steps = document.querySelectorAll(".process-step-card");
    const marker = document.getElementById("railTriangleMarker");
    const railLine = document.getElementById("processActiveRail");

    if (!steps.length || !marker) return;

    ScrollTrigger.create({
        trigger: "#section-process",
        start: "top 70%",
        end: "bottom 60%",
        scrub: 0.8,
        onUpdate: (self) => {
            const p = self.progress; // 0.0 to 1.0
            if (railLine) railLine.style.width = `${p * 100}%`;

            // Calculate marker position percentage
            const markerPos = Math.max(0, Math.min(98, p * 100));
            marker.style.left = `${markerPos}%`;

            // Activate step cards sequentially
            const activeIndex = Math.min(steps.length - 1, Math.floor(p * steps.length));
            steps.forEach((card, idx) => {
                if (idx <= activeIndex) {
                    card.classList.add("step-active");
                    card.classList.remove("step-inactive");
                } else {
                    card.classList.remove("step-active");
                    card.classList.add("step-inactive");
                }
            });
        }
    });

    // Allow clicking on any step to scroll smoothly to that position
    steps.forEach((step, idx) => {
        step.addEventListener("click", () => {
            const targetSection = document.getElementById("section-process");
            if (targetSection) {
                const rect = targetSection.getBoundingClientRect();
                const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
                const sectionTop = rect.top + scrollTop;
                const offset = (idx / (steps.length - 1)) * (rect.height * 0.6);
                window.scrollTo({
                    top: sectionTop + offset,
                    behavior: "smooth"
                });
            }
        });
    });
}

/**
 * Pillar Underline Reveal
 */
function setupPillarHairlines() {
    const pillars = document.querySelectorAll(".pillar-card");
    pillars.forEach((card) => {
        ScrollTrigger.create({
            trigger: card,
            start: "top 85%",
            onEnter: () => {
                const line = card.querySelector(".pillar-hairline-fill");
                if (line) line.style.width = "100%";
            }
        });
    });
}

/**
 * Section 4 (Convergence / CTA) Entrance
 */
function setupConvergenceEntrance() {
    ScrollTrigger.create({
        trigger: "#section-convergence",
        start: "top 65%",
        onEnter: () => {
            gsap.from(".convergence-elem", {
                opacity: 0,
                y: 30,
                stagger: 0.15,
                duration: 0.9,
                ease: "power3.out"
            });
        }
    });
}

/**
 * Cursor Radial Glow Hotspot
 */
function initCursorGlow() {
    const glowEl = document.getElementById("cursorGlow");
    if (!glowEl) return;

    let targetX = window.innerWidth / 2;
    let targetY = window.innerHeight / 2;
    let currentX = targetX;
    let currentY = targetY;

    window.addEventListener("mousemove", (e) => {
        targetX = e.clientX;
        targetY = e.clientY;
    });

    function updateGlow() {
        currentX += (targetX - currentX) * 0.12;
        currentY += (targetY - currentY) * 0.12;
        glowEl.style.transform = `translate(${currentX}px, ${currentY}px) translate(-50%, -50%)`;
        requestAnimationFrame(updateGlow);
    }
    requestAnimationFrame(updateGlow);
}

/**
 * Contact Micro-Form Submission Handler
 */
function initContactForm() {
    const form = document.getElementById("contactMicroForm");
    const nameInput = document.getElementById("contactName");
    const emailInput = document.getElementById("contactEmail");
    const feedbackEl = document.getElementById("formFeedback");

    if (!form) return;

    form.addEventListener("submit", (e) => {
        e.preventDefault();

        const name = nameInput ? nameInput.value.trim() : "";
        const email = emailInput ? emailInput.value.trim() : "";

        if (!email || !email.includes("@")) {
            if (feedbackEl) {
                feedbackEl.innerHTML = `<span class="text-amber-400"><i class="fa-solid fa-triangle-exclamation mr-1.5"></i> Please enter a valid academic or institution email.</span>`;
                feedbackEl.classList.remove("hidden");
            }
            return;
        }

        // Generate synthetic research access token
        const keyHash = Math.random().toString(36).substring(2, 8).toUpperCase();
        if (feedbackEl) {
            feedbackEl.innerHTML = `
                <div class="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 text-xs font-mono shadow-lg shadow-emerald-500/10">
                    <i class="fa-solid fa-circle-check text-emerald-400"></i>
                    <span>ACCESS APPROVED // KEY: <strong>COSMOS-${keyHash}</strong></span>
                    <a href="/dashboard" class="ml-2 underline text-white hover:text-emerald-200">Open Console &rarr;</a>
                </div>
            `;
            feedbackEl.classList.remove("hidden");
        }

        // Clear form
        if (nameInput) nameInput.value = "";
        if (emailInput) emailInput.value = "";
    });
}
