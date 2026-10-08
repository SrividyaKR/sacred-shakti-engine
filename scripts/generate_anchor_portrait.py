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


def image_data_uri(path: Path) -> str:
    mime = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}[path.suffix.lower()]
    return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode()}"


def edit_candidate(args) -> int:
    """Image-to-image pass: edit --base using --reference images, keeping everything the prompt does not mention."""
    if not args.edit_prompt:
        print("--edit-prompt is required with --base", file=sys.stderr)
        return 1
    images = [args.base, *args.reference]
    missing = [str(p) for p in images if not p.exists()]
    if missing:
        print(f"Missing image(s): {', '.join(missing)}", file=sys.stderr)
        return 1
    rep = SemanticGuard().check(args.edit_prompt, [])
    if not rep.ok:
        print("\n".join(f"{f.rule}: {f.message}" for f in rep.findings), file=sys.stderr)
        return 1
    out = args.output or ROOT / "outputs" / "anchors" / args.character / f"{args.character}_candidate_edit.png"
    payload = {
        "model": args.model, "prompt": args.edit_prompt, "aspect_ratio": args.aspect_ratio, "n": 1,
        "output_format": "png",
        "input_references": [{"type": "image_url", "image_url": {"url": image_data_uri(p)}} for p in images],
    }
    print(f"Edit base: {args.base}")
    for i, p in enumerate(args.reference, 2):
        print(f"Reference {i}: {p}")
    print(f"Prompt: {args.edit_prompt}\nOutput: {out}")
    if args.dry_run:
        return 0

    import requests

    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        print("OPENROUTER_API_KEY not set. Add it to .env.", file=sys.stderr)
        return 1
    r = requests.post(IMAGES_URL, json=payload, headers={"Authorization": f"Bearer {key}"}, timeout=300)
    if not r.ok:
        print(f"OpenRouter rejected the request ({r.status_code}): {r.text[:500]}", file=sys.stderr)
        return 1
    item = r.json()["data"][0]
    out.parent.mkdir(parents=True, exist_ok=True)
    if item.get("media_type", "image/png") != "image/png":
        out = out.with_suffix(EXT.get(item["media_type"], out.suffix))
        print(f"Note: the model returned {item['media_type']}, saved as {out.name}")
    out.write_bytes(base64.b64decode(item["b64_json"]))
    print(f"Saved {out}")
    return 0


def main() -> int:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--character", required=True)
    ap.add_argument("--count", type=int, default=2, help="candidate portraits (one request each)")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--aspect-ratio", default="9:16", choices=["9:16", "1:1"])
    ap.add_argument("--dry-run", action="store_true", help="show the prompt, payload and output paths; no API call")
    ap.add_argument("--base", type=Path, help="edit mode: image to edit (pose, face and framing are kept)")
    ap.add_argument("--reference", type=Path, action="append", default=[], help="edit mode: extra reference image (repeatable)")
    ap.add_argument("--edit-prompt", help="edit mode: instruction describing the change")
    ap.add_argument("--output", type=Path, help="edit mode: output path (default: next candidate in outputs/anchors/<id>/)")
    args = ap.parse_args()
    if args.base:
        return edit_candidate(args)

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
