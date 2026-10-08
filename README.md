# Sacred Shakti Engine

An automated multimodal pipeline for **@sacredshaktiAI**, an Instagram project devoted to the **Dasa Mahavidyas**, the Ten Tantric Wisdom Goddesses. The engine turns structured archetype definitions and master reference images into short, reverent, cinematic videos with matching captions, then stages them for human review before posting.

## Principles

- **Reverence first.** Imagery follows traditional iconography. Fierce forms are depicted symbolically and non-graphically.
- **Identity consistency.** Every generation is conditioned on a master anchor image so each goddess looks the same across posts.
- **Human in the loop.** Nothing is published automatically. All output lands in `review_queue/` for approval.
- **Config-driven.** Philosophy, iconography, motion, and caption themes live in JSON, not code.

## Repository Layout

```
.
├── anchors/        Master reference images (e.g. kali_profile_1x1.png, kali_portrait_9x16.png)
├── configs/
│   └── mahavidyas.json   Archetype definitions for all ten Mahavidyas
├── scripts/        Automation code for the pipeline
├── review_queue/   Rendered MP4s and generated metadata (git-ignored)
├── .gitignore
└── README.md
```

## Archetype Config

`configs/mahavidyas.json` defines each of the ten goddesses, in traditional order:

| # | Mahavidya | Core theme |
|---|-----------|------------|
| 1 | Kali | Time, dissolution, liberation |
| 2 | Tara | Compassionate guidance |
| 3 | Tripura Sundari | Supreme beauty and bliss |
| 4 | Bhuvaneshwari | Space and cosmic motherhood |
| 5 | Bhairavi | Inner fire and discipline |
| 6 | Chhinnamasta | Self-sacrifice and transcendence |
| 7 | Dhumavati | Emptiness and renunciation |
| 8 | Bagalamukhi | Stillness and control of speech |
| 9 | Matangi | Inspired expression and art |
| 10 | Kamalatmika | Abundance and fulfillment |

Each entry contains:

- **`sanskrit_title`, `order`, `epithet`**: identity and sequencing.
- **`archetype`**: the core philosophical meaning.
- **`iconography`**: colors, ornaments, sacred geometry, attributes, and setting.
- **`motion`**: camera moves, lighting, atmosphere, and pacing directives for video models.
- **`themes`**: caption hooks, keywords, and hashtags.

A `global` block holds shared style lock, negative prompt, anchor image paths, and output formats.

## Pipeline Architecture

```
 configs/mahavidyas.json ──┐
                           ├─► 1. Prompt Composer ─► 2. Image/Video Generation ─► 3. Post-process
 anchors/*.png ────────────┘                                                         │
                                                                                     ▼
                              review_queue/  ◄─ 5. Metadata & Caption ◄─ 4. Audio & Assembly
                                    │
                                    ▼
                         6. Human review ─► manual post to Instagram
```

1. **Prompt Composer**: merges the selected goddess's iconography, motion directives, and the global style lock into a structured prompt, with the negative prompt applied.
2. **Generation**: an image-to-video model animates the goddess from the anchor image (9:16 for Reels, 1:1 for profile and grid) to preserve identity. The anchor is sent as the first-frame keyframe. See [Video Models](#video-models).
3. **Post-process**: trimming, upscaling, frame-rate and aspect-ratio normalization.
4. **Audio & Assembly**: ambient or devotional soundscape (mantra, drone, instruments) is mixed in and the clip is finalized as an MP4.
5. **Metadata & Caption**: a caption is built from the goddess's hooks and keywords, with hashtags, and written as a sidecar file next to the video.
6. **Review**: outputs are checked for iconographic accuracy, tone, and quality before posting.

> Model and tool choices for stages 3-4 are intentionally pluggable and will be implemented under `scripts/`.

## Video Models

**ByteDance Seedance 2.5 is the recommended (and default) model.** It is built for multi-reference consistency, which matters for iconography: ornaments, skin tone, and sacred symbols stay stable across a clip and across the series. The anchor image is passed as the `first_frame` keyframe, and Seedance can produce up to 30 seconds per clip.

| `--model` | Route | Notes |
|-----------|-------|-------|
| `seedance` / `seedance-2.5` (default) | OpenRouter (`bytedance/seedance-2.5`), or fal.ai (`bytedance/seedance-2.5/image-to-video`) | Provider chosen by `--provider auto`: OpenRouter if `OPENROUTER_API_KEY` is set, otherwise fal.ai if `FAL_KEY` is set |
| a fal.ai model id, e.g. `fal-ai/kling-video/v1.5/pro/image-to-video` or `fal-ai/minimax-video/image-to-video` | fal.ai | Requires `FAL_KEY` |

Seedance has no negative-prompt field, so the engine appends the global negative prompt to the prompt as an "Avoid:" clause. Native audio is off by default (`--audio` enables it) because the soundtrack is added in assembly. On fal.ai, image-to-video takes its aspect ratio from the anchor image.

```bash
cp .env.example .env                      # add OPENROUTER_API_KEY and/or FAL_KEY
python3 scripts/generate.py --goddess kali --model seedance --dry-run   # inspect payload, no cost
python3 scripts/generate.py --goddess kali --duration 10 --resolution 720p
```

Only Kali has anchor images so far; live mode for the other goddesses needs their anchors added under `anchors/` and registered in the config.

## Content Workflow

1. Pick the next Mahavidya (default: by `order`) and a format (Reel 9:16 or profile 1:1).
2. Run the pipeline to render a clip and generate its caption and hashtags.
3. Find the MP4 and metadata in `review_queue/`.
4. Review for reverence, accuracy, and quality; regenerate or edit as needed.
5. Post approved content to Instagram manually.
6. Proceed through the series, Kali to Kamalatmika.

## Status

Foundation scaffold: folder structure, archetype config, and documentation. Pipeline scripts are forthcoming.

## Notes

- Rendered videos (`*.mp4`), `review_queue/`, `.env` secrets, logs, and caches are git-ignored.
- Store API keys in a local `.env` file; never commit them.
