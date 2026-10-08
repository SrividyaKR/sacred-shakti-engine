#!/usr/bin/env python3
"""Sacred Shakti Engine: generate a Mahavidya video prompt, caption and (optionally) render it via fal.ai."""

import argparse
import base64
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "configs" / "mahavidyas.json"
QUEUE_DIR = ROOT / "review_queue"

DEFAULT_MODEL = "seedance"
OPENROUTER_URL = "https://openrouter.ai/api/v1/videos"
# Seedance 2.5 model ids per provider (aliases "seedance" / "seedance-2.5" resolve here).
SEEDANCE = {"openrouter": "bytedance/seedance-2.5", "fal": "bytedance/seedance-2.5/image-to-video"}
SEEDANCE_ALIASES = {"seedance", "seedance-2.5"}
HANDLE = "@sacredshaktiAI"
BASE_HASHTAGS = ["#DasaMahavidya", "#Shakti", "#Tantra", "#SacredFeminine", "#Hinduism", "#sacredshaktiAI"]


class Shot(BaseModel):
    duration: int
    camera: str
    action: str


class Motion(BaseModel):
    camera: str
    action: str = ""
    shots: list[Shot] = Field(default_factory=list)
    lighting: str
    atmosphere: str
    pacing: str


class Iconography(BaseModel):
    colors: list[str]
    ornaments: list[str]
    sacred_geometry: list[str]
    attributes: list[str]
    appearance: list[str] = Field(default_factory=list)
    setting: str


class Themes(BaseModel):
    caption_hooks: list[str]
    keywords: list[str]
    hashtags: list[str]


class Goddess(BaseModel):
    id: str
    order: int
    name: str
    sanskrit_title: str
    epithet: str
    archetype: str
    iconography: Iconography
    motion: Motion
    negative_prompt: str = ""
    themes: Themes


class Metadata(BaseModel):
    goddess: str
    order: int
    model: str
    provider: str
    aspect_ratio: str
    anchor_image: Optional[str]
    motion_prompt: str
    negative_prompt: str
    caption: str
    hashtags: list[str] = Field(default_factory=list)
    generated_at: str
    video_file: Optional[str] = None
    video_url: Optional[str] = None


def load_config() -> dict:
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)


def get_goddess(cfg: dict, goddess_id: str) -> Goddess:
    for entry in cfg["mahavidyas"]:
        if entry["id"] == goddess_id:
            return Goddess(**entry)
    raise SystemExit(f"Unknown goddess '{goddess_id}'")


def timeline(shots: list[Shot]) -> str:
    """Describe consecutive shots as one timed sequence for a single long generation."""
    t, parts = 0, []
    for i, sh in enumerate(shots, 1):
        parts.append(f"Shot {i} ({t}-{t + sh.duration}s): {sh.camera} {sh.action}")
        t += sh.duration
    return " ".join(parts)


def build_motion_prompt(g: Goddess, cfg: dict) -> str:
    ico, mo = g.iconography, g.motion
    parts = [
        f"{g.name}, {g.epithet}, the Hindu Tantric goddess, centered and facing the viewer, exactly matching the reference image.",
        *ico.appearance,
        f"Setting: {ico.setting}",
        f"Palette: {', '.join(ico.colors)}.",
        f"Sacred geometry subtly present: {', '.join(ico.sacred_geometry)}.",
        f"Camera: {mo.camera}",
        *([f"Action: {mo.action}"] if mo.action else []),
        *([timeline(mo.shots)] if mo.shots else []),
        f"Lighting: {mo.lighting}",
        f"Atmosphere: {mo.atmosphere}",
        f"Pacing: {mo.pacing}",
        cfg["global"]["style_lock"],
        "Cinematic, 4K, smooth natural motion, consistent identity and costume throughout.",
    ]
    return " ".join(parts)


def build_hashtags(g: Goddess) -> list[str]:
    seen, tags = set(), []
    for tag in g.themes.hashtags + BASE_HASHTAGS:
        if tag.lower() not in seen:
            seen.add(tag.lower())
            tags.append(tag)
    return tags


def build_caption(g: Goddess, total: int) -> tuple[str, list[str]]:
    hook = g.themes.caption_hooks[0]
    ico = g.iconography
    lore = (
        f"{g.name} ({g.sanskrit_title}), {g.epithet}. {g.archetype} "
        f"She is shown with {', '.join(ico.attributes[:3])}, "
        f"and the {ico.sacred_geometry[0]} marks her yantra, the geometry of her teaching. "
        f"Meditate on {', '.join(g.themes.keywords[:3])}."
    )
    series = f"Part {g.order} of {total}: Dasa Mahavidyas"
    cta = f"Which aspect of {g.name} speaks to you right now? Tell me in the comments."
    tags = build_hashtags(g)
    caption = f"{hook}\n\n{lore}\n\n{series}\n\n{cta}\n\n{' '.join(tags)}"
    return caption, tags


def resolve_anchor(cfg: dict, goddess_id: str, aspect_ratio: str) -> Optional[Path]:
    rel = cfg["global"]["anchor_images"].get(goddess_id, {}).get(f"portrait_{aspect_ratio.replace(':', 'x')}")
    return (ROOT / rel) if rel else None


def with_negative(prompt: str, negative: str) -> str:
    # Seedance has no negative_prompt field, so fold it into the prompt text.
    return f"{prompt} Avoid: {negative}."


def data_uri(path: Path) -> str:
    return f"data:image/png;base64,{base64.b64encode(path.read_bytes()).decode()}"


def resolve_provider(model: str, requested: str) -> str:
    """Pick the API route. Non-Seedance models are always fal; Seedance prefers OpenRouter, falling back to fal."""
    if model not in SEEDANCE_ALIASES:
        return "fal"
    if requested != "auto":
        return requested
    if os.environ.get("OPENROUTER_API_KEY"):
        return "openrouter"
    if os.environ.get("FAL_KEY"):
        return "fal"
    return "openrouter"  # nothing configured yet (dry-run); live mode will report the missing key


def model_id(model: str, provider: str) -> str:
    return SEEDANCE[provider] if model in SEEDANCE_ALIASES else model


def build_payload(model: str, provider: str, prompt: str, negative: str, aspect_ratio: str, duration: str,
                  resolution: str, audio: bool, image: str) -> dict:
    """`image` is a hosted URL or data URI of the first frame."""
    if model in SEEDANCE_ALIASES:
        full = with_negative(prompt, negative)
        if provider == "openrouter":
            return {
                "model": SEEDANCE["openrouter"],
                "prompt": full,
                "frame_images": [{"type": "image_url", "image_url": {"url": image}, "frame_type": "first_frame"}],
                "aspect_ratio": aspect_ratio,
                "duration": int(duration),
                "resolution": resolution,
                "generate_audio": audio,
            }
        # fal image-to-video takes its aspect ratio from the image ("auto" only)
        return {
            "prompt": full, "image_url": image, "duration": duration, "resolution": resolution,
            "aspect_ratio": "auto", "generate_audio": audio,
        }
    if "minimax" in model:
        return {"prompt": prompt, "image_url": image, "prompt_optimizer": True}
    return {
        "prompt": prompt,
        "negative_prompt": negative,
        "image_url": image,
        "duration": duration,
        "aspect_ratio": aspect_ratio,
        "cfg_scale": 0.5,
    }


def render_fal(model: str, payload: dict) -> str:
    import fal_client

    def on_update(update):
        if isinstance(update, fal_client.InProgress):
            for log in update.logs or []:
                print(f"  [fal] {log['message']}")

    print(f"Submitting to fal: {model} (polling until complete)...")
    result = fal_client.subscribe(model, arguments=payload, with_logs=True, on_queue_update=on_update)
    return result["video"]["url"]


def render_openrouter(payload: dict, api_key: str) -> str:
    import requests

    headers = {"Authorization": f"Bearer {api_key}"}
    print(f"Submitting to OpenRouter: {payload['model']}...")
    r = requests.post(OPENROUTER_URL, json=payload, headers=headers, timeout=60)
    if not r.ok:
        raise SystemExit(f"OpenRouter rejected the request ({r.status_code}): {r.text[:500]}")
    job = r.json()
    poll_url = job["polling_url"]
    while True:
        time.sleep(10)
        r = requests.get(poll_url, headers=headers, timeout=60)
        r.raise_for_status()
        job = r.json()
        print(f"  [openrouter] {job['status']}")
        if job["status"] == "completed":
            return job["unsigned_urls"][0]
        if job["status"] == "failed":
            raise SystemExit(f"Generation failed: {job.get('error')}")


def download(url: str, dest: Path, headers: Optional[dict] = None) -> None:
    import requests

    with requests.get(url, headers=headers, stream=True, timeout=120) as r:
        r.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in r.iter_content(1 << 20):
                f.write(chunk)


def main() -> None:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
    cfg = load_config()
    ids = [m["id"] for m in cfg["mahavidyas"]]

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--goddess", default="kali", choices=ids)
    ap.add_argument("--dry-run", action="store_true", help="print prompt/caption/payload without calling the video API")
    ap.add_argument("--model", default=DEFAULT_MODEL,
                    help="'seedance' / 'seedance-2.5' (default), or a fal.ai model id such as "
                         "fal-ai/kling-video/v1.5/pro/image-to-video or fal-ai/minimax-video/image-to-video")
    ap.add_argument("--provider", default="auto", choices=["auto", "openrouter", "fal"],
                    help="Seedance API route; auto = OpenRouter if OPENROUTER_API_KEY is set, else fal if FAL_KEY is set")
    ap.add_argument("--aspect-ratio", default="9:16", choices=["9:16", "1:1"])
    ap.add_argument("--duration", type=int, default=None,
                    help="clip seconds: 4-30 for Seedance, 5 or 10 for Kling/MiniMax (default: total of the goddess's shots, else 5)")
    ap.add_argument("--resolution", default="720p", choices=["480p", "720p", "1080p"], help="Seedance only")
    ap.add_argument("--audio", action="store_true", help="let Seedance generate audio (off by default; soundtrack is added later)")
    args = ap.parse_args()

    g = get_goddess(cfg, args.goddess)
    seedance = args.model in SEEDANCE_ALIASES
    if args.duration is None:
        args.duration = sum(sh.duration for sh in g.motion.shots) or 5
    if not (4 <= args.duration <= 30 if seedance else args.duration in (5, 10)):
        ap.error("--duration must be 4-30 for Seedance, or 5/10 for other models")
    args.duration = str(args.duration)
    prompt = build_motion_prompt(g, cfg)
    negative = ", ".join(filter(None, [cfg["global"]["negative_prompt"], g.negative_prompt]))
    caption, tags = build_caption(g, len(ids))
    anchor = resolve_anchor(cfg, g.id, args.aspect_ratio)
    provider = resolve_provider(args.model, args.provider)
    mid = model_id(args.model, provider)

    meta = Metadata(
        goddess=g.id, order=g.order, model=mid, provider=provider, aspect_ratio=args.aspect_ratio,
        anchor_image=str(anchor.relative_to(ROOT)) if anchor else None,
        motion_prompt=prompt, negative_prompt=negative, caption=caption, hashtags=tags,
        generated_at=datetime.now().isoformat(timespec="seconds"),
    )

    def payload_for(image: str) -> dict:
        return build_payload(args.model, provider, prompt, negative, args.aspect_ratio, args.duration,
                             args.resolution, args.audio, image)

    if args.dry_run:
        payload = payload_for("<first-frame image: data URI or uploaded URL>")
        print("=== MOTION PROMPT ===\n" + prompt)
        print("\n=== CAPTION ===\n" + caption)
        print(f"\n=== PAYLOAD (provider: {provider}, model: {mid}) ===\n" + json.dumps(payload, indent=2, ensure_ascii=False))
        print("\n=== METADATA ===\n" + meta.model_dump_json(indent=2))
        if not anchor or not anchor.exists():
            print(f"\n[warn] no anchor image for '{g.id}' ({args.aspect_ratio}); live mode would fail.", file=sys.stderr)
        return

    key_name = "OPENROUTER_API_KEY" if provider == "openrouter" else "FAL_KEY"
    if not os.environ.get(key_name):
        raise SystemExit(f"{key_name} not set for provider '{provider}'. Copy .env.example to .env and add your key.")
    if not anchor or not anchor.exists():
        raise SystemExit(f"No anchor image for '{g.id}' at {args.aspect_ratio}. Add one under anchors/ and register it in the config.")

    if provider == "openrouter":
        api_key = os.environ[key_name]
        video_url = render_openrouter(payload_for(data_uri(anchor)), api_key)
        dl_headers = {"Authorization": f"Bearer {api_key}"}
    else:
        import fal_client

        print(f"Uploading anchor {anchor.name}...")
        video_url = render_fal(mid, payload_for(fal_client.upload_file(str(anchor))))
        dl_headers = None

    QUEUE_DIR.mkdir(exist_ok=True)
    stem = f"{g.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    mp4 = QUEUE_DIR / f"{stem}.mp4"
    download(video_url, mp4, dl_headers)
    meta.video_file, meta.video_url = str(mp4.relative_to(ROOT)), video_url
    (QUEUE_DIR / f"{stem}.json").write_text(meta.model_dump_json(indent=2), encoding="utf-8")
    print(f"Saved {mp4} and {stem}.json")


if __name__ == "__main__":
    main()
