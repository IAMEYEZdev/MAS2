# The Juice Pantry — The Jungle Awakens 🌿🧃

A cinematic, scroll-driven concept reimagining of [thejuicepantry.com](https://thejuicepantry.com/) —
a full one-page brand site where a jungle comes alive inside the page. Fan-made mock,
not affiliated with the brand.

## View it

Open `index.html` in any modern browser. No build step, no server needed —
GSAP is vendored locally in `vendor/`. Cinematic backdrops are AI-generated
with **Higgsfield Soul** and hotlinked from Higgsfield's CDN; if any image is
unreachable the scene gracefully falls back to the hand-drawn gradient art.

```bash
open juice-pantry-cinematic/index.html      # macOS
xdg-open juice-pantry-cinematic/index.html  # Linux
```

Then **scroll slowly** — the film is driven by the scrollbar.

## The one-page drop

| # | Section | What happens |
|---|---------|--------------|
| 1 | **Hero — The Jungle Awakens** | Higgsfield jungle-cathedral backdrop with Ken Burns drift, parallax canopy, light shafts, mist, fireflies |
| 2 | **The Pour** *(pinned scene)* | The Jungle Gold bottle rises and spins, the cap unscrews and swirls into the canopy, five juice arcs erupt while the bottle drains; droplet particles rain down |
| 3 | **Shop the Pantry** | Six-SKU product grid with prices, spinning bottles, working cart counter and juice-splash add-to-cart bursts |
| 4 | **Field Guide** *(horizontal scroll)* | Four flavor worlds — Green Mamba, Solar Flare, Dragon's Heart, Jungle Gold — each with its own generated biome backdrop, breathing splash, and vines that crawl over the card |
| 5 | **Raw Numbers** | Animated stat counters (2 lbs produce / 0° heat / 48 h press-to-porch / 100 % glass) |
| 6 | **Cleanses** | Three expedition tiers with pricing — Day Trip $39, Expedition $109, Full Jumanji $179 |
| 7 | **Our Story** | Split layout with vine-framed generated artwork and brand lore |
| 8 | **Survivors' Notes** | Testimonial cards |
| 9 | **Let the Jungle In** *(pinned scene)* | Eight procedural vines overgrow the viewport, sprouting leaves and fruit |
| 10 | **Find the Pantry** | Stockist list + working mock newsletter signup |
| 11 | **Finale — Drink the Wild** | Splash crown erupts, the bottle line-up rises, mega-footer with full sitemap |

Persistent cinema layer: film grain, vignette, letterboxing during pinned shots,
corner vines that grow with overall scroll progress, a "nectar" progress bar,
falling leaves in the back half, and a canvas firefly system that gets denser
the deeper you go.

## How it's built

- Single `index.html`; bottles, vines, splashes and gushes are hand-built inline
  SVG, CSS and canvas. No frameworks beyond GSAP.
- **GSAP 3 + ScrollTrigger** (vendored) — pinned scrub timelines, the horizontal
  field guide, parallax/Ken Burns on backdrops, counters, reveals.
- **Higgsfield Soul** (`soul_2`, 2K) — nine art-directed environment plates
  generated on the free plan (~0.12 credits each), hotlinked with a
  min-webp → raw-png → gradient fallback chain.
- **Procedural vine generator** — seeded quadratic-bézier paths with leaves and
  fruit, drawn via stroke-dashoffset.
- Respects `prefers-reduced-motion`.
