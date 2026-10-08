#!/usr/bin/env python3
"""Compile a storyboard against an anchor and run both guards. No LLM, no cost.

    .venv/bin/python scripts/check_storyboard.py --character tara concepts/tara/drafts/the_laugh.json
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.agents.director import Director, Shot  # noqa: E402
from src.agents.validators import MotionGuard, SemanticGuard  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("storyboard", type=Path, help="JSON with a 'shots' list (a concept, or a loop result with 'final')")
    ap.add_argument("--character", required=True)
    ap.add_argument("--show-prompt", action="store_true")
    args = ap.parse_args()
    data = json.loads(args.storyboard.read_text(encoding="utf-8"))
    concept = data.get("final", data)
    anchor = Director().load_anchor(args.character)
    bundle = Director().compose_anchor(anchor, shots=[Shot(**s) for s in concept["shots"]])
    reports = [SemanticGuard().check(bundle.prompt, anchor.negatives, anchor.environment.excluded), MotionGuard().check(bundle.prompt)]
    for rep in reports:
        print(f"[{'PASS' if rep.ok else 'FAIL'}] {rep.guard}")
        for f in rep.findings:
            print(f"    {f.level.upper()} {f.rule}: {f.message}")
    print(f"Duration: {bundle.duration}s, shots: {len(bundle.shots)}")
    if args.show_prompt:
        print("\n" + bundle.prompt)
    return 0 if all(r.ok for r in reports) else 1


if __name__ == "__main__":
    sys.exit(main())
