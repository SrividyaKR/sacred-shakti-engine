#!/usr/bin/env python3
"""Run the concept loop for a deity: Director proposes, critics debate, Director revises until they pass.

    .venv/bin/python scripts/develop_concept.py --character tara
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.agents import concept_loop  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--character", required=True)
    ap.add_argument("--rounds", type=int, default=6)
    ap.add_argument("--candidates", type=int, default=6)
    ap.add_argument("--model", default="", help="OpenRouter text model (default anthropic/claude-sonnet-5.5)")
    args = ap.parse_args()
    res = concept_loop.run(args.character, args.rounds, args.candidates, model=args.model)
    print(f"\n{'APPROVED by all critics' if res['passed'] else 'NOT auto-approved: choose between the finalists below'}"
          f" after {res['rounds']} round(s); {res['llm_calls']} LLM calls, ${res['cost_usd']}")
    for n, fin in enumerate(res["finalists"][: 1 if res["passed"] else 2], 1):
        f = fin["concept"]
        print(f"\n=== FINALIST {n}: {f['title']} ===\nScores: {fin['scores']}  Guard problems: {fin['guard_problems'] or 'none'}")
        print(f"SOURCE SEED: {f.get('source_seed', '')}\nLOGLINE: {f['logline']}\nHOOK: {f['hook']}\nLOOP: {f['loop']}\nSHARE: {f['share_trigger']}")
        print(f"CAPTION HOOK: {f['caption_hook']}\nAUDIO: {f['audio']}")
        for i, sh in enumerate(f["shots"], 1):
            print(f"  Shot {i} ({sh['duration']}s) {sh.get('purpose', '')}\n    camera: {sh['camera']}\n    action: {sh['action']}")
    print(f"\nSaved {res['path']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
