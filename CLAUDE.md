# Sacred Shakti Engine

Multi-agent generative video pipeline for **@sacredshaktiAI**, covering the ten Dasa Mahavidyas. Each agent has one job and passes a typed result to the next. Nothing is posted automatically: renders land in `review_queue/` for human review.

## Pipeline

```
Showrunner -> Director -> Validation Council (concurrent) -> Executor -> QA Vision -> review_queue/
                          ├─ Semantic Guard
                          └─ Motion Guard
```

| Stage | Role | Status |
|-------|------|--------|
| **Series Showrunner** | Owns order and status of the ten deities in `configs/series_manifest.json` (`queued` / `active` / `completed`, `anchor_locked`). Returns the current deity, advances the queue. | `src/agents/showrunner.py` |
| **Character Anchors** | Canonical, locked character definitions: `configs/anchors/<id>.json` (appearance, environment, negatives, reference images). The anchor is the source of truth for how a deity looks. | Kali only |
| **Director Agent** | Reads an anchor and composes the prompt: anchor traits, lighting, and a timed shot plan (eye-level pull-back from the face, then a queenly walk). | `src/agents/director.py` |
| **Semantic Guard** | Deterministic regex audit of the positive prompt: blocks daylight, occult symbols, the trigger words `sacred*` / `mystic*`, Sanskrit/Hindi loanwords and non-ASCII text, and any word the anchor lists under `environment.excluded`. Caps negatives at **6 terms** (comma-separated phrases). | `src/agents/validators.py` |
| **Motion Guard** | Deterministic audit for motion contradictions: jump or hard cuts, hair state changes, non-physical hair, hair without gradual settling, eye-level versus low-angle conflicts, shot timing gaps. | `src/agents/validators.py` |
| **Executor** | Dispatches to the video model (Seedance 2.5 via OpenRouter, fal.ai fallback), polls, downloads the MP4 and writes metadata JSON. | `scripts/run_pipeline.py` (reuses `scripts/generate.py` helpers) |
| **QA Vision** | Samples frames at t=0, mid and end and checks identity, attire and environment drift against the anchor. | **Planned** |

The council runs both guards concurrently and blocks the render if either fails. The Motion Guard's fast-LLM audit (physics and jump-cut review) is **planned**; only its deterministic rules exist today.

## Layout

```
anchors/                  reference images (kali_portrait_9x16.png, kali_profile_1x1.png)
configs/
  series_manifest.json    ordered queue and status
  anchors/<id>.json       canonical character anchors
  mahavidyas.json         archetype, iconography, caption themes (used for captions and by scripts/generate.py)
src/agents/               showrunner.py, director.py, validators.py
scripts/
  run_pipeline.py         orchestrator (use this)
  generate.py             earlier single-script generator; still the source of the API helpers and caption builder
review_queue/             renders and metadata (git-ignored)
```

Manifest ids are identical to the ids in `mahavidyas.json` (including `chhinnamasta` and `kamalatmika`).

## Commands

```bash
.venv/bin/python scripts/run_pipeline.py --character kali --dry-run   # compose + validate, no API, no manifest writes
.venv/bin/python scripts/run_pipeline.py --dry-run                    # current deity from the manifest
.venv/bin/python scripts/run_pipeline.py --next --dry-run             # preview advancing the queue
.venv/bin/python scripts/run_pipeline.py --character kali             # live render (costs money)
```

Exit code is 0 when composition and validation pass, 1 when validation fails or the anchor is missing. `--next` completes the active deity and activates the next queued one (written to the manifest unless `--dry-run`). A live run marks a queued deity `active`; completing it is a deliberate `--next` after review.

## Rules for writing prompts and anchors

- **Positive prompt only describes what to show.** Exclusions go in the anchor's `negatives` (max 6 terms), never as "no X" sentences in the prompt: naming an unwanted thing primes the model.
- **Never use** `sacred`, `mystic`, or occult-symbol vocabulary in prompts. Use "reverent", "devotional", "ornate" instead.
- **Plain English only**: no Sanskrit or Hindi loanwords or non-ASCII text in prompts, anchors or negatives (for example "pleated wrap skirt", not "dhoti"). The Semantic Guard enforces this; deity names are the only exception.
- **Night series**: no daylight vocabulary. Per-anchor exclusions (for example `fire` for Kali) go in `environment.excluded`.
- **Hair and motion**: describe hair as settling gradually under gravity and moving with the stride; never as a state that jumps between shots. Shots must be contiguous (each starts where the last ended).
- **Camera**: eye level, crown framed and centered. No low angle, upward tilt or under-chin views.
- Seedance has no negative-prompt field; the Executor appends negatives as an "Avoid:" clause.
- Anchors are **locked** once approved (`anchor_locked: true`). Change one only deliberately and re-render for review.

## Environment

- Python 3.14 in `.venv/` (`pip install -r requirements.txt`).
- Keys in `.env` (copy `.env.example`): `OPENROUTER_API_KEY` (preferred), `FAL_KEY` (fallback), `ANTHROPIC_API_KEY` (optional, for the planned LLM audit).
- Never commit `.env`, `*.mp4` or `review_queue/`.

## Working agreements

- Live renders cost money (a 10 s, 720p Seedance clip is a few dollars). Run `--dry-run` first and confirm before a live render.
- Confirm before pushing or any other outward-facing action; commit only when asked.
- Only Kali has anchor images and an anchor JSON so far. Each new deity needs both (and `anchor_locked: true`) before a live run.
