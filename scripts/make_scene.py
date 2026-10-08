#!/usr/bin/env python3
"""Scene-first generator: scene JSON -> keyframes (FLUX, portrait as identity reference) -> video draft(s).

    .venv/bin/python scripts/make_scene.py concepts/scenes/n29.json --keyframes
    .venv/bin/python scripts/make_scene.py concepts/scenes/n29.json --video google/veo-3.1-fast --resolution 720p --dry-run

Scene JSON: {id, title, reference, start_prompt, end_prompt (optional), video_prompt, duration}.
Spend is tracked in outputs/scenes/spend.json and refused past --cap (default 8.00 USD).
"""

import argparse
import base64
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

ROOT = Path(__file__).resolve().parent.parent
IMAGES_URL = "https://openrouter.ai/api/v1/images"
VIDEOS_URL = "https://openrouter.ai/api/v1/videos"
MODELS_URL = "https://openrouter.ai/api/v1/videos/models"
CREDITS_URL = "https://openrouter.ai/api/v1/credits"
IMAGE_MODEL = "black-forest-labs/flux.2-pro"
IMAGE_COST = 0.05  # rough per image
TOKEN_MODEL_PER_SECOND = {  # rough USD per second for token-priced models
    "bytedance/seedance-2.0": {"480p": 0.04, "720p": 0.07, "1080p": 0.15},
    "bytedance/seedance-2.0-fast": {"480p": 0.025, "720p": 0.042},
    "bytedance/seedance-2.0-mini": {"480p": 0.02, "720p": 0.035},
    "bytedance/seedance-2.5": {"480p": 0.15, "720p": 0.35},
}


def load_env() -> None:
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def data_uri(path: Path) -> str:
    mime = "image/jpeg" if path.suffix.lower() in (".jpg", ".jpeg") else "image/png"
    return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode()}"


def ledger_path() -> Path:
    return ROOT / "outputs" / "scenes" / "spend.json"


def spent() -> float:
    p = ledger_path()
    return sum(e["usd"] for e in json.loads(p.read_text())) if p.exists() else 0.0


def record(kind: str, scene: str, usd: float, note: str = "") -> None:
    p = ledger_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    rows = json.loads(p.read_text()) if p.exists() else []
    rows.append({"kind": kind, "scene": scene, "usd": round(usd, 4), "note": note, "t": time.strftime("%F %T")})
    p.write_text(json.dumps(rows, indent=2))


def credits_used(key: str):
    import requests
    try:
        d = requests.get(CREDITS_URL, headers={"Authorization": f"Bearer {key}"}, timeout=30).json()["data"]
        return float(d["total_usage"])
    except Exception:
        return None


def video_model_info(model: str) -> dict:
    import requests
    for m in requests.get(MODELS_URL, timeout=30).json()["data"]:
        if m["id"] == model:
            return m
    raise SystemExit(f"Unknown video model {model}. List: curl {MODELS_URL}")


def estimate_video(info: dict, resolution: str, seconds: int) -> float:
    sku = info.get("pricing_skus") or {}
    if info["id"] in TOKEN_MODEL_PER_SECOND:
        return TOKEN_MODEL_PER_SECOND[info["id"]].get(resolution, 0.2) * seconds
    for k in (f"duration_seconds_{resolution}", f"image_to_video_duration_seconds_{resolution}", "duration_seconds",
              "duration_seconds_without_audio", f"duration_seconds_without_audio_{resolution}"):
        if k in sku:
            return float(sku[k]) * seconds
    for k in (f"cents_per_video_output_second_{resolution}", "cents_per_second_output", f"cents_per_second_output_{resolution}"):
        if k in sku:
            return float(sku[k]) / 100 * seconds
    return 0.2 * seconds


def make_keyframes(scene: dict, key: str, cap: float, dry: bool) -> int:
    import requests
    out_dir = ROOT / "outputs" / "scenes" / scene["id"]
    ref = ROOT / scene["reference"]
    for name in ("start", "end"):
        prompt = scene.get(f"{name}_prompt")
        if not prompt:
            continue
        print(f"[{name}] {prompt}")
        if dry:
            continue
        if spent() + IMAGE_COST > cap:
            print("Budget cap reached; stopping.", file=sys.stderr)
            return 1
        payload = {"model": IMAGE_MODEL, "prompt": prompt, "aspect_ratio": "9:16", "n": 1, "output_format": "png",
                   "input_references": [{"type": "image_url", "image_url": {"url": data_uri(ref)}}]}
        r = requests.post(IMAGES_URL, json=payload, headers={"Authorization": f"Bearer {key}"}, timeout=300)
        if not r.ok:
            print(f"OpenRouter rejected the image request ({r.status_code}): {r.text[:400]}", file=sys.stderr)
            return 1
        out_dir.mkdir(parents=True, exist_ok=True)
        dest = out_dir / f"{name}.png"
        dest.write_bytes(base64.b64decode(r.json()["data"][0]["b64_json"]))
        record("keyframe", scene["id"], IMAGE_COST, name)
        print(f"Saved {dest}")
    return 0


def make_video(scene: dict, model: str, resolution: str, key: str, cap: float, dry: bool, use_end: bool, audio: bool) -> int:
    import requests
    info = video_model_info(model)
    seconds = int(scene.get("duration", 10))
    allowed = info.get("supported_durations") or []
    if allowed and seconds not in allowed:
        seconds = min(allowed, key=lambda d: abs(d - seconds))
        print(f"Duration adjusted to {seconds}s for {model}")
    if resolution not in (info.get("supported_resolutions") or [resolution]):
        print(f"{model} supports {info['supported_resolutions']}, not {resolution}", file=sys.stderr)
        return 1
    est = estimate_video(info, resolution, seconds)
    out_dir = ROOT / "outputs" / "scenes" / scene["id"]
    frames = [{"type": "image_url", "image_url": {"url": data_uri(out_dir / "start.png")}, "frame_type": "first_frame"}]
    end = out_dir / "end.png"
    if use_end and end.exists() and "last_frame" in (info.get("supported_frame_images") or []):
        frames.append({"type": "image_url", "image_url": {"url": data_uri(end)}, "frame_type": "last_frame"})
    payload = {"model": model, "prompt": scene["video_prompt"], "frame_images": frames, "aspect_ratio": "9:16",
               "duration": seconds, "resolution": resolution}
    if info.get("generate_audio") is not None:
        payload["generate_audio"] = audio
    print(f"{model} {resolution} {seconds}s, frames={len(frames)}, estimated ${est:.2f}; spent so far ${spent():.2f} of ${cap:.2f}")
    print(f"Prompt: {scene['video_prompt']}")
    if dry:
        return 0
    if spent() + est > cap:
        print("Budget cap would be exceeded; not rendering.", file=sys.stderr)
        return 1
    headers = {"Authorization": f"Bearer {key}"}
    before = credits_used(key)
    r = requests.post(VIDEOS_URL, json=payload, headers=headers, timeout=60)
    if not r.ok:
        print(f"OpenRouter rejected the video request ({r.status_code}): {r.text[:500]}", file=sys.stderr)
        return 1
    poll = r.json()["polling_url"]
    while True:
        time.sleep(10)
        job = requests.get(poll, headers=headers, timeout=60).json()
        print(f"  [{model}] {job['status']}")
        if job["status"] == "completed":
            url = job["unsigned_urls"][0]
            break
        if job["status"] == "failed":
            print(f"Generation failed: {job.get('error')}", file=sys.stderr)
            return 1
    dest = ROOT / "review_queue" / "scenes" / f"{scene['id']}_{model.replace('/', '_')}_{resolution}.mp4"
    dest.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(url, headers=headers, stream=True, timeout=300) as vr:
        vr.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in vr.iter_content(1 << 20):
                f.write(chunk)
    after = credits_used(key)
    actual = (after - before) if before is not None and after is not None and after > before else None
    record("video", scene["id"], actual if actual else est, f"{model} {resolution} {'actual' if actual else 'estimate'}")
    print(f"Saved {dest}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("scene", type=Path)
    ap.add_argument("--keyframes", action="store_true", help="generate start/end keyframes")
    ap.add_argument("--video", action="append", default=[], help="video model id (repeatable)")
    ap.add_argument("--resolution", default="480p")
    ap.add_argument("--no-end-frame", action="store_true")
    ap.add_argument("--audio", action="store_true")
    ap.add_argument("--cap", type=float, default=8.0)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    load_env()
    key = os.environ.get("OPENROUTER_API_KEY", "")
    if not key and not args.dry_run:
        print("OPENROUTER_API_KEY not set.", file=sys.stderr)
        return 1
    scene = json.loads(args.scene.read_text(encoding="utf-8"))
    rc = 0
    if args.keyframes:
        rc = make_keyframes(scene, key, args.cap, args.dry_run) or rc
    for model in args.video:
        rc = make_video(scene, model, args.resolution, key, args.cap, args.dry_run, not args.no_end_frame, args.audio) or rc
    return rc


if __name__ == "__main__":
    sys.exit(main())
