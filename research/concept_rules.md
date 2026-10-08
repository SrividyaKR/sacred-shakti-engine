# Concept rules (shared by the concept agents)

Single source for the director and the critics. The Python loop in `src/agents/concept_loop.py` mirrors this text.
Pass thresholds: feasibility is a RISK FLAG, not a veto (we test with cheap draft renders); authenticity must be at
least 8; virality target 7. A human director makes the final call.

## Hard constraints for a concept
HARD CONSTRAINTS (the concept is rejected automatically if it breaks one):
- One continuous 10 second image-to-video clip made by Seedance 2.5. Seedance renders ONE continuous clip, so write
  exactly 2 beats (an opening and a payoff); the second-by-second split is only a loose guide.
- The FIRST FRAME is the reference portrait and cannot change: the anchor's first_frame field Anything else in the scene (objects, water
  motion, light) must emerge or enter during the clip; it cannot already be there in frame 1. The camera starts on this framing.
- SIMPLICITY BUDGET: besides Her hair settling, at most TWO things may move or change in the whole clip (for example one
  gesture plus one response in the environment). The whole concept must fit in one sentence of 25 words or fewer. No small
  tracked objects, no second object appearing, no camera reversal.
- Total shot durations must add up to exactly 10 seconds, in exactly 2 shots. Each shot has camera, action, purpose.
- Camera stays at horizontal eye level. The crown stays centered and fully framed. No low angle, upward tilt or under-chin views.
- Plain English only. Never use the words sacred, mystic or occult. No Sanskrit or Hindi loanwords. No on-screen text.
- Describe only what to show. Never write "no X", "without X" or "avoid X"; exclusions are handled elsewhere.
- Every gesture or action must name its visible consequence in the same sentence (what it causes in the scene).
- Hair settles gradually under natural gravity. No wind-blown or constantly waving hair.
- Stay inside the anchor's environment and creative palette. Never mention: the words listed in the anchor's environment.excluded.
- One goddess, no other characters, no cuts inside the clip, no fast motion, no hand-held objects that need precise handling.
- AGENCY: the goddess must DO something. She performs one clear, deliberate action (a head turn, a gaze shift, a change
  of expression, a slow lean, a step) that causes one visible change. A passive glow, a hold, or a light-only effect is rejected.
  Prefer actions of the face, head and body; avoid hand gestures and handled objects (the video model renders hands badly).
- SOURCE: build the concept on exactly one named story seed from the research dossier and name it in "source_seed".
  Do not invent legends; if you use an invented symbol, say so in "story".
- Reverent and non-graphic. No memes, no sexualisation, no gore.
- Design for what Seedance renders reliably and AVOID what it renders badly (from research):
(read research/seedance_capabilities.md)

## Virality rubric
VIRALITY RUBRIC (score 1-10). Instagram Reels rewards watch time / completion, sends per reach and saves.
Judge: (1) hook: does visible, specific motion begin in the first 1.5 seconds? (2) hold: is there a payoff or
question that keeps people to the end? (3) loop: does the ending flow back into the opening frame? (4) send-worthiness:
who would send this to whom, and why? (5) save value: would someone keep it? (6) novelty versus generic AI devotional
clips; (7) clarity on a phone screen in a single 10 second clip. Penalise static poses, slow starts, gestures with no
consequence, and generic 'goddess stands there' or glow-only scenes. The goddess must visibly DO something. Do NOT reward spectacle or busyness: one simple, unmistakable
moment that a viewer grasps instantly beats a crowded one, and complexity that the video model cannot render scores low.

## Authenticity rubric
AUTHENTICITY RUBRIC (score 1-10; below 7 is a veto). Does the concept match the research dossier and express the
deity's real meaning and purpose? Is it reverent and non-graphic? Does it avoid trivialising, mixing traditions
without care, or presenting disputed legends as canonical? Would a devotee find it respectful?

## Feasibility rubric
FEASIBILITY RUBRIC (score 1-10). Can Seedance 2.5 render this reliably as one 10 second clip starting from the
reference portrait? Penalise complex hand-object interactions, many moving elements, anything needing text, cuts or
multiple characters, physically implausible motion, and actions with no visible cause and effect. Also fail anything
that is already in frame 1 but not in the reference portrait, more than two moving elements besides settling hair, and any
reliance on second-by-second timing. Prefer a few elements moving clearly and slowly.

## Concept schema
{"id": "A", "title": "...", "source_seed": "which story seed this is built on", "logline": "one sentence", "hook": "what the viewer sees in the first 1.5s",
"story": "what happens and why it matters for this deity", "loop": "how the end connects back to the start",
"share_trigger": "who sends this and why", "caption_hook": "first line of the caption",
"audio": "suggested sound", "shots": [{"duration": 5, "camera": "...", "action": "...", "purpose": "..."}]}
