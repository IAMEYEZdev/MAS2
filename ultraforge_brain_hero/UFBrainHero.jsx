import { useEffect, useRef } from "react";
import "./uf-brain-hero.css";

const GLYPHS = "01アイウエオカキクケコサシスセソタチツテト<>/{}[]=+*#";
const FONT_SIZE = 14;

/**
 * UltraForge animated brain hero.
 *
 * Centerpiece: Higgsfield-generated circuit brain with the UF monogram
 * amalgamated into its pathways (job 25fc4a87-36d3-497d-9f4f-ea6cf5fa812b).
 * Animation is layered in code: matrix rain, breathing glow, shimmer sweep,
 * spark particles, micro-motion and pointer parallax.
 *
 * @param {string}  brainSrc   path to the UF brain still (png)
 * @param {string}  videoSrc   optional Higgsfield video loop (mp4) — when set,
 *                             renders a <video> with brainSrc as poster
 * @param {string}  brand      wordmark text, first and middle initials glow
 * @param {string}  tagline    sub-headline
 * @param {ReactNode} children optional CTA row rendered under the tagline
 */
export default function UFBrainHero({
  brainSrc = "/assets/uf-brain.png",
  videoSrc = null,
  brand = "UltraForge",
  tagline = "The self-orchestrating intelligence layer. One brain, every workflow — forged to build, deploy and scale autonomous agents.",
  children = null,
}) {
  const heroRef = useRef(null);
  const rainRef = useRef(null);
  const sparksRef = useRef(null);
  const mediaRef = useRef(null);

  useEffect(() => {
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const hero = heroRef.current;
    const rain = rainRef.current;
    const sparks = sparksRef.current;
    const rctx = rain.getContext("2d");
    const sctx = sparks.getContext("2d");
    let cols = [];
    let particles = [];
    let raf = 0;

    const newParticle = () => ({
      x: Math.random() * sparks.width,
      y: Math.random() * sparks.height * 0.8,
      r: 0.6 + Math.random() * 1.6,
      vy: -(0.08 + Math.random() * 0.25),
      vx: (Math.random() - 0.5) * 0.12,
      life: Math.random(),
    });

    const resize = () => {
      rain.width = sparks.width = hero.clientWidth;
      rain.height = sparks.height = hero.clientHeight;
      cols = Array.from({ length: Math.floor(rain.width / FONT_SIZE) },
                        () => Math.random() * -100);
      particles = Array.from({ length: Math.max(24, rain.width / 40) }, newParticle);
    };

    const tick = () => {
      rctx.fillStyle = "rgba(0, 0, 0, 0.08)";
      rctx.fillRect(0, 0, rain.width, rain.height);
      rctx.font = `${FONT_SIZE}px monospace`;
      for (let i = 0; i < cols.length; i++) {
        const y = cols[i] * FONT_SIZE;
        rctx.fillStyle = Math.random() > 0.975 ? "#b6ffd9" : "#0fae53";
        rctx.fillText(GLYPHS[(Math.random() * GLYPHS.length) | 0], i * FONT_SIZE, y);
        cols[i] = y > rain.height && Math.random() > 0.985 ? 0 : cols[i] + 0.55;
      }

      sctx.clearRect(0, 0, sparks.width, sparks.height);
      for (const p of particles) {
        p.x += p.vx; p.y += p.vy; p.life += 0.008;
        if (p.life > 1 || p.y < -4) {
          Object.assign(p, newParticle(), { y: sparks.height * (0.5 + Math.random() * 0.4) });
        }
        const a = Math.sin(p.life * Math.PI) * 0.85;
        sctx.beginPath();
        sctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
        sctx.fillStyle = `rgba(140, 255, 190, ${a.toFixed(3)})`;
        sctx.shadowColor = "#19f06e";
        sctx.shadowBlur = 8;
        sctx.fill();
        sctx.shadowBlur = 0;
      }
      raf = requestAnimationFrame(tick);
    };

    const onMove = (e) => {
      const dx = (e.clientX / hero.clientWidth - 0.5) * 14;
      const dy = (e.clientY / hero.clientHeight - 0.5) * 8;
      mediaRef.current.style.translate = `${dx}px ${dy}px`;
    };
    const onLeave = () => { mediaRef.current.style.translate = "0 0"; };

    resize();
    window.addEventListener("resize", resize);
    if (!reduced) {
      raf = requestAnimationFrame(tick);
      if (window.matchMedia("(pointer: fine)").matches) {
        hero.addEventListener("mousemove", onMove);
        hero.addEventListener("mouseleave", onLeave);
      }
    }
    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("resize", resize);
      hero.removeEventListener("mousemove", onMove);
      hero.removeEventListener("mouseleave", onLeave);
    };
  }, []);

  // glow the brand initials: the first letter and the second capital
  // ("UltraForge" → U + F), falling back to the first letter only
  const second = brand.slice(1).search(/[A-Z]/) + 1;

  return (
    <section className="uf-hero" ref={heroRef}>
      <canvas className="uf-hero__rain" ref={rainRef} />
      <div className="uf-hero__glow" />

      <div className="uf-hero__media" ref={mediaRef}>
        {videoSrc ? (
          <video autoPlay muted loop playsInline preload="auto" poster={brainSrc}>
            <source src={videoSrc} type="video/mp4" />
          </video>
        ) : (
          <img src={brainSrc} alt={`${brand} agentic AI circuit brain`} />
        )}
      </div>

      <canvas className="uf-hero__sparks" ref={sparksRef} />

      <div className="uf-hero__copy">
        <p className="uf-hero__eyebrow">Agentic AI</p>
        <h1 className="uf-hero__title">
          <span className="uf">{brand[0]}</span>
          {(second > 0 ? brand.slice(1, second) : brand.slice(1)).toUpperCase()}
          {second > 0 && <span className="uf">{brand[second]}</span>}
          {second > 0 && brand.slice(second + 1).toUpperCase()}
        </h1>
        <p className="uf-hero__sub">{tagline}</p>
        {children && <div className="uf-hero__cta">{children}</div>}
      </div>
    </section>
  );
}
