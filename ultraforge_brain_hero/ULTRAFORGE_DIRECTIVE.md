# UltraForge (UF) Brain Hero — handoff package

**Audience:** the Claude Code session working in the UltraForge landing-page
project. This package was produced in a separate cloud session (MAS2 repo,
branch `claude/sharp-tesla-9h0l4w`) because the reference image could not be
attached in the terminal. It implements the owner's directive: take the
"digital brain" banner (green circuit-board brain, dark metallic orbital
rings, matrix code rain), amalgamate the **UF** initials into the brain, make
it animated/moving, and place it in the UltraFold/UltraForge landing-page
hero.

## What's in here

| File | Purpose |
|------|---------|
| `fetch_assets.sh` | Downloads the Higgsfield-generated brain into `assets/` — **run this first** |
| `uf-brain-hero.html` | Self-contained hero section (vanilla HTML/CSS/JS) — open in a browser to preview |
| `UFBrainHero.jsx` + `uf-brain-hero.css` | React component port, asset paths and brand text as props |
| `assets/` | Target directory for the generated media |

## The generated asset

- **Higgsfield job:** `25fc4a87-36d3-497d-9f4f-ea6cf5fa812b` (image,
  Nano Banana Pro, 16:9, 2752×1536) — also visible in the owner's
  Higgsfield library.
- Glowing emerald circuit-board brain on pure black, **"UF" monogram fused
  into the central circuitry**, dark glossy orbital rings, matrix code rain
  backdrop — faithful to the reference banner.

## Animation approach

Higgsfield video models (Kling 3.0, Grok Imagine, Grok 1.5) are all gated
behind a paid plan on the owner's current free tier, so the motion is layered
in code on top of the still — which loops seamlessly forever and stays crisp:

1. Canvas matrix code rain behind the brain (full hero width).
2. Breathing radial glow (`uf-breathe`).
3. Energy shimmer sweeping the circuit traces (`uf-shimmer`, screen blend).
4. Foreground spark particles drifting upward (canvas).
5. Micro float/scale motion on the brain (`uf-float`) + pointer parallax.
6. `prefers-reduced-motion` disables all of it gracefully.

### Upgrading to a true generated video later

If the owner upgrades the Higgsfield plan, generate a 3–5s loop with model
`kling3_0` (`sound: "off"`), passing job `25fc4a87-36d3-497d-9f4f-ea6cf5fa812b`
as **both** `start_image` and `end_image` for a seamless loop, with a
locked-camera ambient-motion prompt. Then drop the mp4 in
`assets/uf-brain-loop.mp4` — the HTML has a commented video slot, and the
React component takes `videoSrc`. All code-driven layers stack cleanly on top.

## Integration

```bash
./fetch_assets.sh                # pull the brain PNG
open uf-brain-hero.html          # preview the hero standalone
```

Then either copy the hero `<section>` + styles + script into the landing
page, or import the React component:

```jsx
import UFBrainHero from "./UFBrainHero";

<UFBrainHero
  brainSrc="/assets/uf-brain.png"
  brand="UltraForge"            // or "UltraFold" — initials auto-glow
  tagline="Your copy here"
>
  <button className="uf-btn uf-btn--primary">Enter the Forge</button>
</UFBrainHero>
```

Brand colors live in CSS variables (`--uf-green` etc.) at the top of the
stylesheet. The headline/tagline/CTAs are placeholders — defer to the full
directive already given to the UltraForge session for final copy.
