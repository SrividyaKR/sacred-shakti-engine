"""Concept loop: the Director proposes video concepts, three critics argue with it, and it revises until they pass.

Evidence behind the virality rubric (Instagram Reels, 2026 sources): ranking leans on watch time / completion,
sends per reach (strongest for reaching non-followers) and likes per reach. Saves and sends weigh more than likes
(third-party estimates). A strong first 1.5-3 seconds and a loop back to the start are practitioner heuristics, not
confirmed by Instagram. Nothing here can predict virality; real signal only comes from posting and measuring.
"""

import json
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

from src.agents.director import Anchor, Director, Shot
from src.agents.llm import LLM
from src.agents.validators import MotionGuard, SemanticGuard

ROOT = Path(__file__).resolve().parents[2]
PASS_SCORE = 8  # authenticity gate
FEASIBILITY_GATE = 8  # hard gate: never spend credits on a concept the video model cannot render
VIRALITY_TARGET = 7

CONSTRAINTS = """HARD CONSTRAINTS (the concept is rejected automatically if it breaks one):
- One continuous {total} second image-to-video clip made by Seedance 2.5. Seedance renders ONE continuous clip, so write
  exactly 2 beats (an opening and a payoff); the second-by-second split is only a loose guide.
- The FIRST FRAME is the reference portrait and cannot change: {first_frame} Anything else in the scene (objects, water
  motion, light) must emerge or enter during the clip; it cannot already be there in frame 1. The camera starts on this framing.
- SIMPLICITY BUDGET: besides Her hair settling, at most TWO things may move or change in the whole clip (for example one
  gesture plus one response in the environment). The whole concept must fit in one sentence of 25 words or fewer. No small
  tracked objects, no second object appearing, no camera reversal.
- Total shot durations must add up to exactly {total} seconds, in exactly 2 shots. Each shot has camera, action, purpose.
- Camera stays at horizontal eye level. The crown stays centered and fully framed. No low angle, upward tilt or under-chin views.
- Plain English only. Never use the words sacred, mystic or occult. No Sanskrit or Hindi loanwords. No on-screen text.
- Describe only what to show. Never write "no X", "without X" or "avoid X"; exclusions are handled elsewhere.
- Every gesture or action must name its visible consequence in the same sentence (what it causes in the scene).
- Hair settles gradually under natural gravity. No wind-blown or constantly waving hair.
- Stay inside the anchor's environment and creative palette. Never mention: {excluded}.
- One goddess, no other characters, no cuts inside the clip, no fast motion, no hand-held objects that need precise handling.
- AGENCY: the goddess must DO something. She performs one clear, deliberate action (a head turn, a gaze shift, a change
  of expression, a slow lean, a step) that causes one visible change. A passive glow, a hold, or a light-only effect is rejected.
  Prefer actions of the face, head and body; avoid hand gestures and handled objects (the video model renders hands badly).
- SOURCE: build the concept on exactly one named story seed from the research dossier and name it in "source_seed".
  Do not invent legends; if you use an invented symbol, say so in "story".
- Reverent and non-graphic. No memes, no sexualisation, no gore.
- Design for what Seedance renders reliably and AVOID what it renders badly (from research):
{capabilities}
"""

RUBRIC = """VIRALITY RUBRIC (score 1-10). Instagram Reels rewards watch time / completion, sends per reach and saves.
Judge: (1) hook: does visible, specific motion begin in the first 1.5 seconds? (2) hold: is there a payoff or
question that keeps people to the end? (3) loop: does the ending flow back into the opening frame? (4) send-worthiness:
who would send this to whom, and why? (5) save value: would someone keep it? (6) novelty versus generic AI devotional
clips; (7) clarity on a phone screen in a single 10 second clip. Penalise static poses, slow starts, gestures with no
consequence, and generic 'goddess stands there' or glow-only scenes. The goddess must visibly DO something. Do NOT reward spectacle or busyness: one simple, unmistakable
moment that a viewer grasps instantly beats a crowded one, and complexity that the video model cannot render scores low."""

AUTHENTICITY = """AUTHENTICITY RUBRIC (score 1-10; below 7 is a veto). Does the concept match the research dossier and express the
deity's real meaning and purpose? Is it reverent and non-graphic? Does it avoid trivialising, mixing traditions
without care, or presenting disputed legends as canonical? Would a devotee find it respectful?"""

FEASIBILITY = """FEASIBILITY RUBRIC (score 1-10). Can Seedance 2.5 render this reliably as one 10 second clip starting from the
reference portrait? Penalise complex hand-object interactions, many moving elements, anything needing text, cuts or
multiple characters, physically implausible motion, and actions with no visible cause and effect. Also fail anything
that is already in frame 1 but not in the reference portrait, more than two moving elements besides settling hair, and any
reliance on second-by-second timing. Prefer a few elements moving clearly and slowly."""

SCHEMA = """{"id": "A", "title": "...", "source_seed": "which story seed this is built on", "logline": "one sentence", "hook": "what the viewer sees in the first 1.5s",
"story": "what happens and why it matters for this deity", "loop": "how the end connects back to the start",
"share_trigger": "who sends this and why", "caption_hook": "first line of the caption",
"audio": "suggested sound", "shots": [{"duration": 5, "camera": "...", "action": "...", "purpose": "..."}]}"""


def _setting(llm: LLM, system: str, user: str, **kw) -> dict:
    return llm.ask_json(system, user, **kw)


def capabilities() -> str:
    return (ROOT / "research" / "seedance_capabilities.md").read_text(encoding="utf-8")


def first_frame(anchor: Anchor) -> str:
    if anchor.first_frame:
        return anchor.first_frame
    return (f"a front-facing, waist-up portrait of {anchor.name} at eye level, crown centered and fully framed, "
            "eyes open with a calm expression, a starry midnight sky behind Her, and nothing else in the frame.")


def guard_problems(anchor: Anchor, concept: dict, total: int) -> list[str]:
    """Deterministic checks: schema, durations, then the same guards the pipeline runs."""
    try:
        shots = [Shot(**s) for s in concept["shots"]]
    except Exception as e:  # malformed concept
        return [f"invalid shots: {e}"]
    problems = []
    if sum(s.duration for s in shots) != total:
        problems.append(f"shot durations add up to {sum(s.duration for s in shots)}s, need exactly {total}s")
    if len(shots) != 2:
        problems.append("need exactly 2 shots")
    action_text = " ".join(sh.action for sh in shots)
    if not re.search(r"\b(turns?|tilts?|lowers?|raises?|lifts?|steps?|walks?|leans?|nods?|bows?|smiles?|laughs?|softens?|looks (?:up|down|toward|away|out|at))\b", action_text, re.IGNORECASE):
        problems.append("no clear action by the goddess (turn, step, lean, expression change); passive concepts are rejected")
    if len(concept.get("logline", "").split()) > 25:
        problems.append("logline is longer than 25 words; the concept must fit in one short sentence")
    prompt = Director().compose_anchor(anchor, shots=shots).prompt
    for rep in (SemanticGuard().check(prompt, anchor.negatives, anchor.environment.excluded), MotionGuard().check(prompt)):
        problems += [f"{rep.guard} {f.rule}: {f.message}" for f in rep.findings]
    return problems


def critique(llm: LLM, name: str, rubric: str, dossier: str, concepts: list[dict]) -> dict:
    system = (f"You are the {name}, a demanding reviewer on a team making Instagram Reels about the Dasa Mahavidyas. "
              f"Be specific and blunt. Do not flatter.\n\n{rubric}")
    user = (f"RESEARCH DOSSIER:\n{dossier}\n\nCONCEPTS TO REVIEW:\n{json.dumps(concepts, indent=1)}\n\n"
            'Return {"evaluations": [{"id": "<concept id>", "score": <1-10>, "issues": ["..."], "fixes": ["..."]}]} '
            "with one evaluation per concept.")
    out = llm.ask_json(system, user, temperature=0.3)
    return {e["id"]: e for e in out["evaluations"]}


def propose(llm: LLM, dossier: str, anchor: Anchor, total: int, n: int, history: list[str]) -> list[dict]:
    system = ("You are the Director of a short-form devotional video series. You invent concepts that are both "
              "reverent and strongly watchable, and you justify every shot with a purpose.")
    user = (f"RESEARCH DOSSIER:\n{dossier}\n\nCHARACTER ANCHOR:\n{anchor.model_dump_json(indent=1, exclude={'shots'})}\n\n"
            f"{CONSTRAINTS.format(total=total, excluded=', '.join(anchor.environment.excluded), first_frame=first_frame(anchor), capabilities=capabilities())}\n{RUBRIC}\n\n"
            f"Titles already used in the series (do not repeat their ideas): {history or 'none'}\n\n"
            f"Propose {n} clearly different concepts, ids A, B, C... Each follows this schema:\n{SCHEMA}\n"
            'Return {"concepts": [ ... ]}.')
    return llm.ask_json(system, user, temperature=1.0, max_tokens=16000)["concepts"]


def revise(llm: LLM, dossier: str, anchor: Anchor, total: int, concept: dict, feedback: list[str]) -> dict:
    system = "You are the Director. Revise your concept to fix every piece of feedback while keeping what works."
    user = (f"RESEARCH DOSSIER:\n{dossier}\n\n{CONSTRAINTS.format(total=total, excluded=', '.join(anchor.environment.excluded), first_frame=first_frame(anchor), capabilities=capabilities())}\n"
            f"CURRENT CONCEPT:\n{json.dumps(concept, indent=1)}\n\nFEEDBACK TO FIX:\n- " + "\n- ".join(feedback) +
            f"\n\nReturn the full revised concept (same id) in this schema:\n{SCHEMA}")
    return llm.ask_json(system, user, temperature=0.7)


def run(character_id: str, rounds: int = 6, candidates: int = 6, total: int = 10, model: str = "") -> dict:
    llm = LLM(model) if model else LLM()
    director = Director()
    anchor = director.load_anchor(character_id)
    dossier = (ROOT / "research" / f"{character_id}.md").read_text(encoding="utf-8")
    history = [json.loads(p.read_text())["final"]["title"] for p in sorted((ROOT / "concepts").glob("*/*.json"))
               if p.parent.name != character_id] if (ROOT / "concepts").exists() else []

    concepts = propose(llm, dossier, anchor, total, candidates, history)
    log, best, passed, stale, best_score = [], None, False, 0, -1
    for rnd in range(1, rounds + 1):
        print(f"Round {rnd}: reviewing {len(concepts)} concept(s)...")
        roles = {"virality": ("Virality Critic", RUBRIC), "authenticity": ("Authenticity Critic", AUTHENTICITY),
                 "feasibility": ("Feasibility Critic", FEASIBILITY + "\n\nWHAT SEEDANCE RENDERS WELL AND BADLY:\n" + capabilities())}
        with ThreadPoolExecutor(max_workers=3) as pool:
            futures = {k: pool.submit(critique, llm, n, r, dossier, concepts) for k, (n, r) in roles.items()}
            reviews = {k: f.result() for k, f in futures.items()}
        scored = []
        for c in concepts:
            cid = c["id"]
            scores = {k: int(reviews[k].get(cid, {}).get("score", 0)) for k in roles}
            problems = guard_problems(anchor, c, total)
            feedback = [f"{k}: {i}" for k in roles for i in reviews[k].get(cid, {}).get("issues", [])]
            feedback += [f"{k} fix: {x}" for k in roles for x in reviews[k].get(cid, {}).get("fixes", [])]
            feedback += [f"guard: {p}" for p in problems]
            ok = (scores["feasibility"] >= FEASIBILITY_GATE and scores["authenticity"] >= PASS_SCORE
                  and scores["virality"] >= VIRALITY_TARGET and not problems)
            scored.append({"concept": c, "scores": scores, "guard_problems": problems, "feedback": feedback, "passed": ok})
            print(f"  {cid} {c.get('title', '')!r}: {scores} guards={'ok' if not problems else len(problems)} {'PASS' if ok else ''}")
        scored.sort(key=lambda s: (s["passed"], s["scores"]["feasibility"] >= FEASIBILITY_GATE and not s["guard_problems"],
                                    s["scores"]["feasibility"], s["scores"]["virality"]), reverse=True)
        log.append({"round": rnd, "results": scored})
        best = scored[0]
        if best["passed"]:
            passed = True
            break
        score = min(best["scores"].values()) - (10 if best["guard_problems"] else 0)
        stale = 0 if score > best_score else stale + 1
        best_score = max(best_score, score)
        if stale >= 2:  # two rounds without improvement: stop spending and let the human choose
            print("  No improvement for 2 rounds; stopping so you can choose.")
            break
        if rnd < rounds:
            with ThreadPoolExecutor(max_workers=2) as pool:
                concepts = list(pool.map(lambda s: revise(llm, dossier, anchor, total, s["concept"], s["feedback"]), scored[:2]))

    result = {"character": character_id, "passed": passed, "rounds": len(log), "model": llm.model,
              "cost_usd": round(llm.cost, 4), "llm_calls": llm.calls, "final": best["concept"],
              "final_scores": best["scores"],
              "finalists": [{"concept": r["concept"], "scores": r["scores"], "guard_problems": r["guard_problems"]}
                            for r in sorted((r for rd in log for r in rd["results"]), key=lambda r: (
                                r["passed"], r["scores"]["feasibility"] >= FEASIBILITY_GATE and not r["guard_problems"],
                                r["scores"]["feasibility"], r["scores"]["virality"]), reverse=True)[:2]], "final_guard_problems": best["guard_problems"],
              "created": datetime.now().isoformat(timespec="seconds"), "transcript": log}
    out = ROOT / "concepts" / character_id
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    result["path"] = str(path.relative_to(ROOT))
    return result
