---
name: media-gen
description: Generate and upscale AI images and videos via Fal.ai using a curated registry of best-in-class models. Use whenever the user asks to create, generate, make, render, or produce a photo, image, picture, or video. Phrases like "make me an image of...", "generate a video of...", "create a photo where...", "I want a picture of...", "turn this into a video". Also use to upscale or enhance an existing video or image to HD ("upscale this", "make this HD", "sharpen this clip"). Workflow refines the prompt with reasoning, picks the current best model from models.json, generates locally to a dated folder, and conversationally offers to animate the image into video.
---

# Media Gen Skill

Local image and image-to-video pipeline that hits Fal.ai. You own the pipeline; models are swappable via `models.json`. No vendor lock-in, no bloated UIs.

> **Path note:** Examples below use the Mac/Linux script path `~/.claude/skills/media-gen/scripts/generate.py`. On Windows, substitute your full path, e.g. `C:\Users\<you>\.claude\skills\media-gen\scripts\generate.py`.

## Operating principles

1. **Refine the prompt before sending it.** The user's casual description is the brief, not the prompt. Use reasoning to expand it into a strong prompt that matches the chosen model's style.
2. **Pick the model from `models.json`.** Default unless the user specifies. Mention model age if the registry is stale.
3. **Be conversational, not form-driven.** Ask one question at a time, accept defaults, don't list ten parameters at once.
4. **Save everything locally.** Each generation gets its own dated folder.
5. **Don't auto-animate.** Always ask "want to turn this into a video?" first. Never assume.
6. **Quote video cost before running.** Fal bills video by the second. Before any `generate.py video` call, read `unit_price_per_second_usd` from `models.json` for the chosen model, compute `price x duration x N videos`, state it, and wait for an explicit yes. Default duration is **5s**, never 10s. Only go to 10s after the user approves the concept at 5s. Image gen is cheap (~$0.05/image) and runs autonomously.
7. **Reuse reference images for character consistency.** When the user wants the same character, face, or style across multiple generations, pass earlier output images as references via `--input-image` (repeatable). See the "Character consistency" section below.

## Workflow

### Step 1: Read user intent

The user gives a casual description, e.g. *"a photo of a dog swimming with a tennis ball."*

Extract:
- **Subject and action** (the literal thing)
- **Implicit style cues** (photo, illustration, cinematic, etc.)
- **Working title**, a 3-5 word kebab-case slug (`dog-swimming-tennis-ball`). Don't ask for this; derive it. Only confirm if genuinely ambiguous.

### Step 2: Refine the prompt

Expand the brief into a strong prompt (2-4 sentences). Add lighting, composition, lens/camera language, environment detail, and mood. Match the target model's preferred prompt style. Nano Banana Pro likes natural-language descriptive prompts, NOT weighted token syntax (`(masterpiece:1.4)` etc).

Show the user the refined prompt. Ask: **"Run this, or want to adjust?"**

If they edit, accept their edits as the source of truth.

### Step 3: Pick the model

Read `models.json`. Use `image.default` unless the user names a specific model.

If `last_updated` in models.json is more than 30 days old, mention it once: *"Model registry was last updated [date]. Want me to refresh it via fal.ai before generating?"* Don't nag if the user says no.

### Step 4: Generate the image

Run the script:

```bash
python ~/.claude/skills/media-gen/scripts/generate.py image \
  --prompt "<refined prompt>" \
  --title "<working-title>" \
  [--model <model-key>] \
  [--aspect-ratio "16:9"] \
  [--resolution "2K"] \
  [--input-image "<ref-path>" --input-image "<ref-path>" ...]
```

`--input-image` is repeatable. Pass one or more reference images to lock character, style, or wardrobe to a prior generation (Nano Banana Pro reads them as `image_urls`). See the **Character consistency** section for the workflow.

The script prints a JSON line with `image_path` and `folder`. Display the local path.

If the script errors with `FAL_KEY not set`, tell the user to run `setx FAL_KEY "<key>"` (Windows) or add `export FAL_KEY="<key>"` to `~/.zshrc` (Mac), then restart the terminal. Don't try to set it for them.

If it errors with `ModuleNotFoundError: fal_client`, tell them to run `pip install fal-client`.

If it errors `404` on the model, the `fal_id` in models.json drifted. Direct them to fal.ai/models, find the new slug, update the JSON.

### Step 5: Offer animation

After the image saves, ask: **"Want to turn this into a video?"**

If yes, conversationally collect (one question, two at most, don't overload them):

- **Motion prompt:** what should happen in the video? This is *different* from the image prompt. ("The dog paddles forward, water splashing, slight camera dolly in.")
- **Duration:** default **5s**. Do not propose 10s as a first option. Only escalate to 10s if the user explicitly asks after seeing a 5s draft.

Then **quote the cost and wait for confirmation** before running:

1. Look up `unit_price_per_second_usd` for the chosen model in `models.json`.
2. State the math: *"{model} = ${price}/s x {duration}s x {N} videos = ${total}."*
3. If the field is missing or marked stale in the registry, WebFetch `https://fal.ai/models/{fal_id}` to get current per-second pricing before quoting. Don't guess.
4. Ask: **"OK to run at this cost?"** and wait for an explicit yes.

Once approved, run:

```bash
python ~/.claude/skills/media-gen/scripts/generate.py video \
  --image "<image_path>" \
  --prompt "<motion prompt>" \
  --title "<working-title>" \
  --folder "<folder from step 4>" \
  --duration 5 \
  [--model <model-key>] \
  [--resolution "1080p"]
```

## Upscaling video and images (Topaz)

Use the `upscale` command to make an existing video or image sharper and higher-resolution. It runs Topaz on Fal.

```bash
python ~/.claude/skills/media-gen/scripts/generate.py upscale \
  --input "<path to source video or image>" \
  [--target-height 1080] \
  [--factor 2] \
  [--fps 30] \
  [--type video|image] \
  [--model <model-key>]
```

**How it avoids stretching (important).** The script reads the source dimensions with ffprobe and applies a *single* `upscale_factor` to both axes. It never hard-sets a width and height, so the aspect ratio is always preserved. This is the #1 cause of "stretched width-wise" upscales: forcing a non-16:9 source into a fixed 1920x1080. This script cannot do that.

- `--target-height` (default 1080): the script computes the factor from the source height to hit this. Aspect preserved.
- `--factor`: override with an explicit multiplier instead. Takes precedence over target-height.
- Input type is inferred from the file extension; force it with `--type` if needed.

**Quote cost before running video upscales.** Topaz video bills per second of output:

- up to 720p: ~$0.01/s
- 720p to 1080p: ~$0.02/s
- above 1080p: ~$0.08/s
- **Price DOUBLES if the output is 60fps.**

So for a 60fps source going to 1080p, either accept the doubled rate, or pass `--fps 30` to re-encode the source to 30fps first (the script does this locally before upload, halving the cost). State the math (`$/s x seconds = $total`) and wait for an explicit yes before running, same as the video gen rule. Image upscales are cheap (per-image, not per-second) and run autonomously.

**Reality check to set expectations.** Upscaling sharpens and cleans; it does not invent detail that was never captured. A very soft or low-bitrate source comes out cleaner but won't become true crisp HD. Best on footage that's already decent but just low-resolution.

The output saves as `upscaled-NN.mp4` / `upscaled-NN.png` in a dated folder, with a `prompt.md` recording the source dimensions and factor used.

## Character consistency

To keep the same character, face, wardrobe, or visual style across multiple generations, pass earlier output images as references via `--input-image` on the image command.

**Important: use the edit variant when passing references.** The default `nano-banana-pro` is text-to-image only and silently ignores `image_urls`. For reference-driven generation, pass `--model nano-banana-pro-edit` (which maps to `fal-ai/nano-banana-pro/edit`). The registry's `best_for` notes flag this.

**Typical workflow:**

1. Generate the first image normally (the "anchor", the character's establishing shot). Save the path.
2. For each subsequent generation of the *same* character, pass the anchor image (and optionally other strong prior frames) via `--input-image`, and switch to the edit model:

   ```bash
   python ~/.claude/skills/media-gen/scripts/generate.py image \
     --prompt "<new scene, same character>" \
     --title "<series-title>" \
     --model nano-banana-pro-edit \
     --input-image "<path to anchor image-01.png>" \
     [--input-image "<path to other prior frame>" ...]
   ```

3. Phrase the prompt as *"the same man from the reference image, now [doing new action / in new setting]"*. Don't redescribe the character's face; let the reference carry it. Describe the new scene, lighting, pose, and mood.
4. The script copies each reference into the output folder as `source-<filename>` so you have provenance.

**When to use:**

- Multi-shot Reels / Shorts where the same person needs to appear in different scenes.
- Building out a "look" or aesthetic across a campaign (same color palette, same wardrobe).
- Iterating on a single character with small variations of the same anchor shot.

**When NOT to use:**

- One-off images with no continuity needs (it just slows the gen).
- When you *want* a different person or style. References will fight your prompt.

**Limits:**

- Only the **image** command accepts references. Image-to-video models (Kling, Seedance) take a single input image and animate it; they don't accept additional refs.
- More than ~3 references tends to muddy results. Pass the strongest 1-2 anchors.
- Reference images are uploaded to Fal each run; the same 10 MB upload limit applies (use 2K resolution for anchors so they stay small).

### Output structure

Each generation creates one folder, all artifacts inside:

```
~/Documents/Media Gen/2026-04-28-dog-swimming-tennis-ball/
├── prompt.md            # full metadata: prompts, models, params, timestamps
├── image-01.png
└── video-01.mp4         # only if the video step ran
```

If you regenerate within the same session, increment: `image-02.png`, etc.

## Updating the model registry

When fal.ai releases a new model and the user asks to refresh:

1. WebSearch / WebFetch fal.ai/models filtered by image and video modalities.
2. Compare against `models.json` and flag any new top-tier additions.
3. Propose updates: bump `default` if a new clear winner exists, add new entries with `fal_id`, `best_for`, and a one-line note.
4. Update `last_updated` to today.
5. Show the user the diff before writing.

## Rules of thumb

- **Don't drift from the user's intent.** Refining a prompt is not rewriting the vision. If they say "a dog," don't decide it should be a golden retriever.
- **One generation per request.** Don't preemptively generate variants unless asked.
