#!/usr/bin/env python3
"""Generate candidate reference portraits for a deity from its anchor JSON, for human approval.

    .venv/bin/python scripts/generate_anchor_portrait.py --character tara --dry-run
"""

import argparse
import base64
import os
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.agents.director import Director  # noqa: E402
from src.agents.validators import SemanticGuard  # noqa: E402

IMAGES_URL = "https://openrouter.ai/api/v1/images"
DEFAULT_MODEL = "black-forest-labs/flux.2-pro"
EXT = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp"}


def main() -> int:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--character", required=True)
    ap.add_argument("--count", type=int, default=2, help="candidate portraits (one request each)")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--aspect-ratio", default="9:16", choices=["9:16", "1:1"])
    ap.add_argument("--dry-run", action="store_true", help="show the prompt, payload and output paths; no API call")
    args = ap.parse_args()

    director = Director()
    try:
        anchor = director.load_anchor(args.character)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    prompt = director.compose_portrait(anchor)
    rep = SemanticGuard().check(prompt, anchor.negatives, anchor.environment.excluded)
    print(f"[{'PASS' if rep.ok else 'FAIL'}] SemanticGuard")
    for f in rep.findings:
        print(f"    {f.level.upper()} {f.rule}: {f.message}")
    if not rep.ok:
        return 1

    full_prompt = f"{prompt} Avoid: {', '.join(anchor.negatives)}."
    payload = {"model": args.model, "prompt": full_prompt, "aspect_ratio": args.aspect_ratio, "n": 1}
    out_dir = ROOT / "outputs" / "anchors" / anchor.id
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    paths = [out_dir / f"{anchor.id}_candidate_{i}_{stamp}.png" for i in range(1, args.count + 1)]

    if args.dry_run:
        print(f"\n=== PROMPT ===\n{full_prompt}")
        print(f"\n=== REQUEST (x{args.count}, POST {IMAGES_URL}) ===")
        print({k: v for k, v in payload.items() if k != "prompt"})
        print("\n=== OUTPUT PATHS ===")
        for p in paths:
            print(p.relative_to(ROOT))
        return 0

    import requests

    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        print("OPENROUTER_API_KEY not set. Add it to .env.", file=sys.stderr)
        return 1
    out_dir.mkdir(parents=True, exist_ok=True)
    saved = []
    for i, path in enumerate(paths, 1):
        print(f"Generating candidate {i}/{args.count} with {args.model}...")
        r = requests.post(IMAGES_URL, json=payload, headers={"Authorization": f"Bearer {key}"}, timeout=300)
        if not r.ok:
            print(f"OpenRouter rejected the request ({r.status_code}): {r.text[:500]}", file=sys.stderr)
            return 1
        item = r.json()["data"][0]
        dest = path.with_suffix(EXT.get(item.get("media_type", "image/png"), ".png"))
        dest.write_bytes(base64.b64decode(item["b64_json"]))
        saved.append(dest)

    print("\nCandidates for review:")
    for p in saved:
        print(f"  {p}")
    print(f"\nTo approve one: copy it to anchors/{anchor.id}_portrait_{args.aspect_ratio.replace(':', 'x')}.png, "
          f"then set anchor_locked to true in configs/anchors/{anchor.id}.json and configs/series_manifest.json.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
