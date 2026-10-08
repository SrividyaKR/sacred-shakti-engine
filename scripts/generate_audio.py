#!/usr/bin/env python3
"""Generate an ambient music bed with Google Lyria 3 (OpenRouter), trimmed to 15 s with fades for looping.

    .venv/bin/python scripts/generate_audio.py --character tara --label a --prompt-file concepts/tara/drafts/call_laugh_welcome_music.txt

Writes assets/audio/<id>/raw_<label>_30s.mp3 and assets/audio/<id>/<id>_option_<label>_15s.mp3 (about $0.04 per clip).
Copy the chosen option to assets/audio/<id>/<id>_theme_15s.mp3 and run_pipeline.py will mux it into renders.
"""

import argparse
import base64
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "google/lyria-3-clip-preview"


def generate(prompt: str, model: str) -> tuple[bytes, float]:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        raise SystemExit("OPENROUTER_API_KEY not set. Add it to .env.")
    r = requests.post(URL, headers={"Authorization": f"Bearer {key}"}, stream=True, timeout=600,
                      json={"model": model, "messages": [{"role": "user", "content": prompt}],
                            "modalities": ["text", "audio"], "stream": True})
    if not r.ok:
        raise SystemExit(f"OpenRouter rejected the request ({r.status_code}): {r.text[:400]}")
    chunks, cost = [], 0.0
    for line in r.iter_lines(decode_unicode=True):
        if not line or not line.startswith("data:"):
            continue
        payload = line[5:].strip()
        if payload == "[DONE]":
            break
        ev = json.loads(payload)
        cost = float((ev.get("usage") or {}).get("cost") or cost)
        for ch in ev.get("choices", []):
            audio = ch.get("delta", {}).get("audio")
            if isinstance(audio, dict) and audio.get("data"):
                chunks.append(audio["data"])
    if not chunks:
        raise SystemExit("No audio came back from the model.")
    return base64.b64decode("".join(chunks)), cost


def trim(raw: Path, out: Path, seconds: int = 15) -> None:
    if not shutil.which("ffmpeg"):
        raise SystemExit("ffmpeg not found (brew install ffmpeg).")
    fade_out = seconds - 1.5
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", str(raw), "-t", str(seconds),
           "-af", f"afade=t=in:ss=0:d=0.5,afade=t=out:st={fade_out}:d=1.5", str(out)]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode:
        raise SystemExit(f"ffmpeg failed: {res.stderr[:300]}")


def mix(music: Path, drums: Path, out: Path, drum_gain: float = 0.8) -> None:
    """Layer a percussion stem under the music (both already trimmed and faded)."""
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", str(music), "-i", str(drums), "-filter_complex",
           f"[1:a]volume={drum_gain}[d];[0:a][d]amix=inputs=2:duration=first:dropout_transition=0:normalize=0,alimiter=limit=0.95",
           str(out)]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode:
        raise SystemExit(f"ffmpeg failed: {res.stderr[:300]}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--character", required=True)
    ap.add_argument("--label", default="a")
    ap.add_argument("--prompt-file", type=Path, required=True)
    ap.add_argument("--model", default=MODEL)
    ap.add_argument("--seconds", type=int, default=15)
    ap.add_argument("--mix", nargs=3, metavar=("MUSIC", "DRUMS", "OUT"), type=Path,
                    help="layer DRUMS under MUSIC into OUT (no generation)")
    ap.add_argument("--drum-gain", type=float, default=0.8)
    ap.add_argument("--from-raw", type=Path, help="skip generation and trim an existing raw mp3")
    args = ap.parse_args()
    if args.mix:
        mix(*args.mix, drum_gain=args.drum_gain)
        print(f"Mixed {args.mix[2]}")
        return 0
    out_dir = ROOT / "assets" / "audio" / args.character
    out_dir.mkdir(parents=True, exist_ok=True)
    raw = out_dir / f"raw_{args.label}_30s.mp3"
    if args.from_raw:
        shutil.copy(args.from_raw, raw)
    else:
        data, cost = generate(args.prompt_file.read_text(encoding="utf-8"), args.model)
        raw.write_bytes(data)
        print(f"Generated {raw.relative_to(ROOT)} (${cost})")
    out = out_dir / f"{args.character}_option_{args.label}_{args.seconds}s.mp3"
    trim(raw, out, args.seconds)
    print(f"Trimmed {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
