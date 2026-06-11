# The Juice Pantry — The Jungle Awakens 🌿🧃

A cinematic, scroll-driven concept reimagining of [thejuicepantry.com](https://thejuicepantry.com/) —
as if a jungle came alive inside the website. Fan-made mock, not affiliated with the brand.

## View it

Open `index.html` in any modern browser. No build step, no server needed
(GSAP is vendored locally in `vendor/`; the only external request is Google Fonts,
which degrades gracefully offline).

```bash
open juice-pantry-cinematic/index.html      # macOS
xdg-open juice-pantry-cinematic/index.html  # Linux
```

Then **scroll slowly** — the whole film is driven by the scrollbar.

## The five scenes

1. **The Jungle Awakens** — misty hero with drifting light shafts, a parallax
   canopy, and fireflies that multiply the deeper you scroll.
2. **The Pour** *(pinned)* — the Jungle Gold bottle rises, spins on its axis,
   the cap unscrews and swirls off into the canopy, and five arcs of juice
   erupt while the bottle visibly drains. Letterbox bars close in for the shot.
3. **Creatures of the Pantry** *(horizontal)* — four flavor worlds
   (Green Mamba, Solar Flare, Dragon's Heart, Jungle Gold), each with a
   spinning bottle, a breathing splash, and procedural vines that crawl over
   the card as it enters frame.
4. **Let the Jungle In** *(pinned)* — eight procedurally grown vines overtake
   the viewport, sprouting leaves and fruit as the headline punches through.
5. **Drink the Wild** — a splash crown erupts, the full bottle line-up rises,
   and falling leaves close the film.

## How it's built

- Single `index.html` — every visual is hand-built inline SVG, CSS, or canvas.
  No images, no frameworks beyond GSAP.
- **GSAP 3 + ScrollTrigger** (vendored) for pinned, scrubbed timelines and the
  horizontal section.
- **Procedural vine generator** — wiggly quadratic-bézier paths with leaves and
  fruit, drawn via stroke-dashoffset; used for the corner overgrowth, the
  flavor cards, and the takeover scene.
- **Canvas FX layer** — fireflies, gravity-simulated juice droplets emitted
  from the bottle mouth mid-pour, and drifting leaves.
- Film grain, vignette, animated letterboxing, and a "nectar" scroll-progress
  bar for the cinematic finish. Respects `prefers-reduced-motion`.
