#!/usr/bin/env python3
"""Sacred Shakti Engine orchestrator: Showrunner -> Director -> Validation Council -> Executor."""

import argparse
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import generate as gen  # noqa: E402  (reuses the fal/OpenRouter helpers, caption builder and config loader)
from src.agents.director import Director, Shot  # noqa: E402
from src.agents.showrunner import Showrunner  # noqa: E402
from src.agents.validators import MotionGuard, SemanticGuard  # noqa: E402


def run_council(bundle, excluded):
    """Run both guards concurrently and return their reports."""
    with ThreadPoolExecutor(max_workers=2) as pool:
        sem = pool.submit(SemanticGuard().check, bundle.prompt, bundle.negatives, excluded)
        mot = pool.submit(MotionGuard().check, bundle.prompt)
        return [sem.result(), mot.result()]


def print_reports(reports) -> None:
    for rep in reports:
        print(f"[{'PASS' if rep.ok else 'FAIL'}] {rep.guard}")
        for f in rep.findings:
            print(f"    {f.level.upper()} {f.rule}: {f.message}")


def execute(args, bundle, anchor_path: Path, payload_for, provider: str, model_id: str) -> Path:
    """Executor: dispatch to the video API, poll, download the MP4 into review_queue/."""
    key_name = "OPENROUTER_API_KEY" if provider == "openrouter" else "FAL_KEY"
    if not os.environ.get(key_name):
        raise SystemExit(f"{key_name} not set for provider '{provider}'. Add it to .env.")
    if not anchor_path.exists():
        raise SystemExit(f"Reference image missing: {anchor_path}")

    if provider == "openrouter":
        api_key = os.environ[key_name]
        video_url = gen.render_openrouter(payload_for(gen.data_uri(anchor_path)), api_key)
        dl_headers = {"Authorization": f"Bearer {api_key}"}
    else:
        import fal_client

        print(f"Uploading {anchor_path.name}...")
        video_url = gen.render_fal(model_id, payload_for(fal_client.upload_file(str(anchor_path))))
        dl_headers = None

    gen.QUEUE_DIR.mkdir(exist_ok=True)
    mp4 = gen.QUEUE_DIR / f"{bundle.character}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
    gen.download(video_url, mp4, dl_headers)
    return mp4


def main() -> int:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--character", help="deity id (default: the manifest's active or next queued deity)")
    ap.add_argument("--next", action="store_true", help="advance the queue: complete the active deity, activate the next")
    ap.add_argument("--dry-run", action="store_true", help="compose and validate only; no API calls, no manifest writes")
    ap.add_argument("--model", default=gen.DEFAULT_MODEL)
    ap.add_argument("--provider", default="auto", choices=["auto", "openrouter", "fal"])
    ap.add_argument("--aspect-ratio", default="9:16", choices=["9:16", "1:1"])
    ap.add_argument("--resolution", default="720p", choices=["480p", "720p", "1080p"])
    ap.add_argument("--audio", action="store_true")
    ap.add_argument("--duration", type=int, default=None, help="override seconds (default: total of the shot plan)")
    ap.add_argument("--storyboard", type=Path, help="JSON with an approved concept (shots, caption_hook); replaces the template shot plan")
    args = ap.parse_args()

    showrunner = Showrunner()
    if args.next:
        if args.character:
            ap.error("--next and --character are mutually exclusive")
        deity = showrunner.advance(write=not args.dry_run)
        note = " (preview, manifest unchanged)" if args.dry_run else ""
        print(f"Queue advanced{note}: {deity.id if deity else 'series complete'}")
    else:
        deity = showrunner.get(args.character) if args.character else showrunner.current()
    if deity is None:
        print("Nothing left in the queue.")
        return 0
    print(f"Showrunner: #{deity.order} {deity.id} [{deity.status}, anchor_locked={deity.anchor_locked}]")

    try:
        anchor = Director().load_anchor(deity.id)
    except FileNotFoundError as e:
        print(f"Director: {e}", file=sys.stderr)
        return 1
    aspect_key = "portrait_" + args.aspect_ratio.replace(":", "x")
    concept = {}
    if args.storyboard:
        data = json.loads(args.storyboard.read_text(encoding="utf-8"))
        concept = data.get("final", data)
        bundle = Director().compose_anchor(anchor, aspect_key, [Shot(**sh) for sh in concept["shots"]])
        print(f"Storyboard: {concept.get('title', args.storyboard.name)} ({bundle.duration}s)")
    else:
        bundle = Director().compose(deity.id, aspect_key)
    if args.duration:
        bundle.duration = args.duration

    reports = run_council(bundle, anchor.environment.excluded)
    print_reports(reports)
    if not all(r.ok for r in reports):
        print("Validation failed; nothing was sent to the video API.", file=sys.stderr)
        return 1

    cfg = gen.load_config()
    goddess = gen.get_goddess(cfg, deity.id)
    caption, tags = gen.build_caption(goddess, len(showrunner.deities))
    if concept.get("caption_hook"):
        caption = caption.split("\n\n", 1)[1].join([concept["caption_hook"] + "\n\n", ""]) if False else concept["caption_hook"] + "\n\n" + caption.split("\n\n", 1)[1]
    negative = ", ".join(bundle.negatives)
    provider = gen.resolve_provider(args.model, args.provider)
    model_id = gen.model_id(args.model, provider)

    def payload_for(image: str) -> dict:
        return gen.build_payload(args.model, provider, bundle.prompt, negative, args.aspect_ratio,
                                 str(bundle.duration), args.resolution, args.audio, image)

    ref = ROOT / bundle.reference_image if bundle.reference_image else None
    meta = {
        "character": bundle.character, "order": deity.order, "provider": provider, "model": model_id,
        "aspect_ratio": args.aspect_ratio, "duration": bundle.duration,
        "reference_image": bundle.reference_image, "prompt": bundle.prompt, "negatives": bundle.negatives,
        "caption": caption, "hashtags": tags, "storyboard": str(args.storyboard) if args.storyboard else None, "generated_at": datetime.now().isoformat(timespec="seconds"),
    }

    if args.dry_run:
        print("\n=== PROMPT ===\n" + bundle.prompt)
        print("\n=== NEGATIVES ===\n" + negative)
        print("\n=== CAPTION ===\n" + caption)
        print(f"\n=== PAYLOAD (provider: {provider}, model: {model_id}) ===")
        print(json.dumps(payload_for("<first-frame image: data URI or uploaded URL>"), indent=2, ensure_ascii=False))
        return 0

    if not (deity.anchor_locked and anchor.anchor_locked):
        raise SystemExit(f"'{deity.id}' anchor is not locked (manifest: {deity.anchor_locked}, anchor file: "
                         f"{anchor.anchor_locked}). Approve a reference portrait and lock it before a live render.")
    if ref is None:
        raise SystemExit(f"No {args.aspect_ratio} reference image in the anchor for '{deity.id}'.")
    if deity.status == "queued":
        showrunner.set_status(deity.id, "active")
    mp4 = execute(args, bundle, ref, payload_for, provider, model_id)
    meta["video_file"] = str(mp4.relative_to(ROOT))
    mp4.with_suffix(".json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Saved {mp4}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
