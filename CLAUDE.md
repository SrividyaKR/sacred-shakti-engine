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
| **Character Anchors** | Canonical, locked character definitions: `configs/anchors/<id>.json` (appearance, environment, creative palette, negatives, reference images). The anchor is the source of truth for how a deity looks and moves. | Kali (locked), Tara (locked) |
| **Iconography Archivist** | Translates a deity's classical iconography into the strict anchor schema (appearance, attire, ornamentation, environment, exactly 6 negatives) in plain English, validates it against both guards, and writes `configs/anchors/<id>.json` with `anchor_locked: false`. Visual canon, including the creative palette, is curated in `CANON` (Tara so far) and must be reviewed by a human. | `src/agents/archivist.py` |
| **Director Agent** | Reads an anchor and composes the prompt: anchor traits, lighting, and a timed shot plan chosen by the anchor's `creative_palette.motion_archetype`, plus its signature phenomena. | `src/agents/director.py` |
| **Semantic Guard** | Deterministic regex audit of the positive prompt: blocks daylight, occult symbols, the trigger words `sacred*` / `mystic*`, Sanskrit/Hindi loanwords and non-ASCII text, and any word the anchor lists under `environment.excluded`. Caps negatives at **6 terms** (comma-separated phrases). | `src/agents/validators.py` |
| **Motion Guard** | Deterministic audit for motion contradictions: jump or hard cuts, hair state changes, non-physical hair, hair without gradual settling, eye-level versus low-angle conflicts, a stationary figure that also walks, shot timing gaps. | `src/agents/validators.py` |
| **Anchor Portrait Generator** | Renders 2 candidate reference portraits from an anchor via OpenRouter's image API (default `black-forest-labs/flux.2-pro`) into `outputs/anchors/<id>/` for human approval. | `scripts/generate_anchor_portrait.py` |
| **Executor** | Dispatches to the video model (Seedance 2.5 via OpenRouter, fal.ai fallback), polls, downloads the MP4 and writes metadata JSON. | `scripts/run_pipeline.py` (reuses `scripts/generate.py` helpers) |
| **QA Vision** | Samples frames at t=0, mid and end and checks identity, attire and environment drift against the anchor. | **Planned** |

The council runs both guards concurrently and blocks the render if either fails. The Motion Guard's fast-LLM audit (physics and jump-cut review) is **planned**; only its deterministic rules exist today.

## Agent Contracts

Each agent is a plain, deterministic Python module with a typed input and output. Agents do not call each other except through the orchestrator (`scripts/run_pipeline.py`).

**Showrunner** (`src/agents/showrunner.py`)
- *In:* `configs/series_manifest.json`. *Out:* a `Deity` (`order`, `id`, `status`, `anchor_locked`).
- `current()` is the active deity, else the first queued; `None` means the series is complete. `advance()` completes the active deity and activates the next queued one.
- Invariants: at most one deity is `active`; ids match `mahavidyas.json`; it writes the manifest only through `set_status` / `advance(write=True)`, and a dry-run never writes.

**Archivist** (`src/agents/archivist.py`)
- *In:* a deity id (must be in the manifest and in `mahavidyas.json`, with a visual canon in `CANON`). *Out:* `configs/anchors/<id>.json` plus notes on classical elements it left out.
- Invariants: plain English only (glossary-translated, deity name excepted); exactly 6 negatives; a `creative_palette` with at least one signature phenomenon; the composed video and portrait prompts pass both guards; it always writes `anchor_locked: false` and never locks an anchor; it refuses to overwrite a locked anchor without `--force`.
- Locking is a human decision after approving a reference portrait.

**Director** (`src/agents/director.py`)
- *In:* an `Anchor`. *Out:* a `PromptBundle` (`prompt`, `negatives`, `shots`, `duration`, `reference_image`), or a still-image portrait prompt.
- A pure function of the anchor: the same anchor always gives byte-identical output (Kali's locked prompt must not change). The prompt is positive-only; exclusions travel as `negatives`.
- The shot plan comes from `creative_palette.motion_archetype` (a missing palette means `grounded_stride`); an anchor's own `shots` override it. Shot durations are contiguous and `duration` is their sum.

**Pre-Render Guards** (`src/agents/validators.py`)
- *In:* the composed prompt, the negatives, and the anchor's `excluded` words. *Out:* a `Report` per guard (`ok`, `findings`).
- Both guards run concurrently and have no side effects. Any `error` finding blocks the render, the orchestrator exits 1, and nothing is sent to a paid API.
- Semantic Guard: daylight, occult symbols, `sacred*` / `mystic*`, non-English terms, anchor exclusions, negative cap (6). Motion Guard: abrupt cuts, hair physics and continuity, camera contradictions, stationary-versus-locomotion contradictions, shot timing.

## Creative Palette

Each anchor may carry a `creative_palette` that tells the Director how the deity moves and what the environment does, so a deity is not forced into the walk cycle.

| Field | Meaning |
|-------|---------|
| `elemental_domain` | The element or setting that shapes the scene's physics. Rendered as "Elemental domain: ..." in the prompt. |
| `motion_archetype` | `grounded_stride` (opening pull-back, then a forward walk toward the viewer), `stationary_command` (opening pull-back, then planted and commanding with a steady camera), or `atmospheric_arc` (opening pull-back, then the camera arcs at eye level around a composed figure). |
| `signature_phenomena` | Physical dynamics unique to the deity, written as things to show. Rendered as "Physical dynamics throughout: ...". |

```json
"creative_palette": {
  "elemental_domain": "reflective dark ocean shore, distant starlight, solitary guiding star",
  "motion_archetype": "stationary_command",
  "signature_phenomena": ["expanding concentric ripples across calm dark water", "...", "slow deliberate arm gesture"]
}
```

All three archetypes share the same eye-level opening pull-back from the face. The Archivist requires a palette for every new anchor. Kali predates the palette and has none, which the Director treats as `grounded_stride`.

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
.venv/bin/python -m src.agents.archivist tara                        # write configs/anchors/tara.json (unlocked)
.venv/bin/python scripts/generate_anchor_portrait.py --character tara --dry-run   # then without --dry-run (costs money)
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
- **Anchor approval workflow** for a new deity: run the Archivist, generate portrait candidates, pick one by eye, copy it to `anchors/<id>_portrait_9x16.png`, then set `anchor_locked: true` in both `configs/anchors/<id>.json` and `configs/series_manifest.json`. A live video render refuses to run until both are true.
- Kali and Tara are locked. Tara's reference portrait is `outputs/anchors/tara/tara-anchor.jpeg`.
