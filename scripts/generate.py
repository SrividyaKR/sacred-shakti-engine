#!/usr/bin/env python3
"""Sacred Shakti Engine: generate a Mahavidya video prompt, caption and (optionally) render it via fal.ai."""

import argparse
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

DEFAULT_MODEL = "fal-ai/kling-video/v1.5/pro/image-to-video"
HANDLE = "@sacredshaktiAI"
BASE_HASHTAGS = ["#DasaMahavidya", "#Shakti", "#Tantra", "#SacredFeminine", "#Hinduism", "#sacredshaktiAI"]


class Motion(BaseModel):
    camera: str
    lighting: str
    atmosphere: str
    pacing: str


class Iconography(BaseModel):
    colors: list[str]
    ornaments: list[str]
    sacred_geometry: list[str]
    attributes: list[str]
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
    themes: Themes


class Metadata(BaseModel):
    goddess: str
    order: int
    model: str
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


def build_motion_prompt(g: Goddess, cfg: dict) -> str:
    ico, mo = g.iconography, g.motion
    parts = [
        f"{g.name}, {g.epithet}, the Hindu Tantric goddess, centered and facing the viewer, exactly matching the reference image.",
        f"Setting: {ico.setting}",
        f"Palette: {', '.join(ico.colors)}.",
        f"Sacred geometry subtly present: {', '.join(ico.sacred_geometry)}.",
        f"Camera: {mo.camera}",
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


def build_payload(model: str, prompt: str, negative: str, aspect_ratio: str, duration: str, image_url: str) -> dict:
    if "minimax" in model:
        return {"prompt": prompt, "image_url": image_url, "prompt_optimizer": True}
    return {
        "prompt": prompt,
        "negative_prompt": negative,
        "image_url": image_url,
        "duration": duration,
        "aspect_ratio": aspect_ratio,
        "cfg_scale": 0.5,
    }


def render(model: str, payload: dict) -> str:
    import fal_client

    def on_update(update):
        if isinstance(update, fal_client.InProgress):
            for log in update.logs or []:
                print(f"  [fal] {log['message']}")

    print(f"Submitting to {model} (polling until complete)...")
    result = fal_client.subscribe(model, arguments=payload, with_logs=True, on_queue_update=on_update)
    return result["video"]["url"]


def download(url: str, dest: Path) -> None:
    import requests

    with requests.get(url, stream=True, timeout=120) as r:
        r.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in r.iter_content(1 << 20):
                f.write(chunk)


def main() -> None:
    cfg = load_config()
    ids = [m["id"] for m in cfg["mahavidyas"]]

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--goddess", default="kali", choices=ids)
    ap.add_argument("--dry-run", action="store_true", help="print prompt/caption/payload without calling the video API")
    ap.add_argument("--model", default=DEFAULT_MODEL, help=f"fal.ai model id (default {DEFAULT_MODEL}; also fal-ai/minimax-video/image-to-video)")
    ap.add_argument("--aspect-ratio", default="9:16", choices=["9:16", "1:1"])
    ap.add_argument("--duration", default="5", choices=["5", "10"], help="clip seconds (Kling)")
    args = ap.parse_args()

    g = get_goddess(cfg, args.goddess)
    prompt = build_motion_prompt(g, cfg)
    negative = cfg["global"]["negative_prompt"]
    caption, tags = build_caption(g, len(ids))
    anchor = resolve_anchor(cfg, g.id, args.aspect_ratio)

    meta = Metadata(
        goddess=g.id, order=g.order, model=args.model, aspect_ratio=args.aspect_ratio,
        anchor_image=str(anchor.relative_to(ROOT)) if anchor else None,
        motion_prompt=prompt, negative_prompt=negative, caption=caption, hashtags=tags,
        generated_at=datetime.now().isoformat(timespec="seconds"),
    )

    if args.dry_run:
        payload = build_payload(args.model, prompt, negative, args.aspect_ratio, args.duration, "<uploaded anchor URL>")
        print("=== MOTION PROMPT ===\n" + prompt)
        print("\n=== CAPTION ===\n" + caption)
        print("\n=== PAYLOAD ===\n" + json.dumps({"model": args.model, "arguments": payload}, indent=2, ensure_ascii=False))
        print("\n=== METADATA ===\n" + meta.model_dump_json(indent=2))
        if not anchor or not anchor.exists():
            print(f"\n[warn] no anchor image for '{g.id}' ({args.aspect_ratio}); live mode would fail.", file=sys.stderr)
        return

    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
    if not os.environ.get("FAL_KEY"):
        raise SystemExit("FAL_KEY not set. Copy .env.example to .env and add your key.")
    if not anchor or not anchor.exists():
        raise SystemExit(f"No anchor image for '{g.id}' at {args.aspect_ratio}. Add one under anchors/ and register it in the config.")

    import fal_client

    print(f"Uploading anchor {anchor.name}...")
    image_url = fal_client.upload_file(str(anchor))
    payload = build_payload(args.model, prompt, negative, args.aspect_ratio, args.duration, image_url)
    video_url = render(args.model, payload)

    QUEUE_DIR.mkdir(exist_ok=True)
    stem = f"{g.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    mp4 = QUEUE_DIR / f"{stem}.mp4"
    download(video_url, mp4)
    meta.video_file, meta.video_url = str(mp4.relative_to(ROOT)), video_url
    (QUEUE_DIR / f"{stem}.json").write_text(meta.model_dump_json(indent=2), encoding="utf-8")
    print(f"Saved {mp4} and {stem}.json")


if __name__ == "__main__":
    main()
