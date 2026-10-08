# Lessons learned (the feedback loop)

Every agent reads this file before working (director, critics, researcher, QA). After EVERY piece of human feedback on a portrait, concept, render or audio, append an entry in the format below. The goal is that the next deity starts smarter than the last.

## How an entry is written
- **Date / deity / stage** (anchor, concept, render, audio)
- **Shown:** what the director was shown
- **Feedback:** the director's words, quoted
- **Change made:** what was changed in response
- **Rule for next time:** one sentence that generalises (this is what agents act on)

## Standing rules (distilled from feedback so far)
1. **The agents do the creative work.** The human is the director and approves; do not hand work back. Generic concepts (a smile, a glow, a slow push-in) get rejected. Never copy another character's motion unless the story demands it.
2. **Ground concepts in research.** Each concept names a story seed from the cited dossier. No invented legends; keep a "not found" list.
3. **Every action has a visible consequence.** No pointless gestures (a raised hand with nothing happening was rejected).
4. **Hair settles under natural gravity.** Words like wind, breeze or drifting made hair wave far too much. Use only "settles under natural gravity".
5. **Feasibility scores are guesses.** Verified real renders (see research/seedance_capabilities.md) outrank an LLM critic's opinion. Test with cheap 480p drafts before paying for 720p. Walking toward the camera, arm swing, a fierce laugh and slowly opening arms all rendered well.
6. **Money.** Show compiled prompts before spending; confirm each paid render; track the real cost from the OpenRouter balance. Subagent work runs on the Claude Pro plan; OpenRouter is for image, video and music only.
7. **Anchor approval.** Present several real alternatives (not near-duplicates), with what differs, the video-suitability risks, and a clear question. After approval, copy to anchors/<id>_portrait_9x16.<ext>, lock the anchor in both the anchor file and the manifest.
8. **Audio.** The director wants an eerie, solemn mood, not a slow heartbeat; faster, more authentic percussion than the first Lyria attempt. Generated music follows words loosely; ask the director for tempo and reference descriptions up front.

## Log
### 2026-10-07 / Kali / render
- **Shown:** repeated 5 s and 10 s Seedance renders, iterating on camera and costume.
- **Feedback:** wanted an eye-level pull-back from the face then a majestic walk, natural hair, matched brocade attire, ominous midnight lighting, no fire or geometry symbols; final version "excellent".
- **Change made:** per-shot plan, hair "settles under natural gravity", anchor-driven attire, exclusions in negatives.
- **Rule for next time:** rules 3 and 4 above.

### 2026-10-08 / Tara / concept
- **Shown:** a stationary raised-hand beat, then several debated concepts, then three non-walking drafts.
- **Feedback:** "when Tara is raising her hand, nothing else is happening... why is she raising her hand"; hair "waving too much, like there is wind"; "it's really generic. I want her to do something"; "what is the point of having AI agents?"; loved the fierce laugh and the open arms.
- **Change made:** purposeless-gesture guard, story-seed research, agency requirement in the director rules, combined Call, Laugh, Welcome storyboard (rendered 15 s, "excellent").
- **Rule for next time:** rules 1 to 5 above.

### 2026-10-08 / Tara / audio
- **Shown:** two Lyria music options plus a Nordic-drum layer.
- **Feedback:** "I do not like your music. The drum beats are too slow. They don't sound like Nordic drum beats. I wanted a very eerie and solemn feeling." Audio skipped for Tara.
- **Change made:** audio deferred to the next deity.
- **Rule for next time:** rule 8 above.

### 2026-10-08 / Tripura Sundari / anchor (round 1)
- **Shown:** five portrait variants: standing rose-crimson, lotus throne, golden-red, full moon, sovereign (concepts/tripura_sundari/anchor_variants.json). QA found shared gaps: skin came out tan, not rose-crimson; no rose-gold glow; only v2 had water.
- **Feedback:** "v2_lotus is a close one. I would try and do one more round of generation, by making this version of her slightly younger. she is 16 in this form. this image makes her look 30."
- **Change made:** second round: edits of v2 only (younger face), plus one fresh generation. Rendered as a youthful adult (early twenties, ageless), never as a literal 16-year-old.
- **Rule for next time:** (a) Tripura Sundari is a youthful goddess; the age read is a key approval criterion, so check it first. (b) For any deity whose iconography says a child or teenager, depict a youthful adult. (c) A seated lotus-throne pose can be the preferred first frame even though the video model finds laps and hands risky: clean up hands rather than switching pose.

### 2026-10-08 / Tripura Sundari / anchor (round 2): LOCKED
- **Shown:** four younger variants of v2 (younger edit, younger plus rose skin, younger plus clean hands, fresh generation). QA recommended the fresh generation for age and hands; flagged v2c for a blue day-like sky and the arms moving outward.
- **Feedback:** "i like the v2c_younger hands version. let us lock that in"
- **Change made:** locked v2c as anchors/tripura_sundari_portrait_9x16.png. The written anchor was rewritten to match the image (blue twilight sky, warm golden-peach skin, seated full-length on a gold lotus with both arms open, palms up). New `seated_presence` motion archetype so a seated deity is never told she "stands".
- **Rule for next time:** (a) The director's eye overrides QA's ranking: record the preference, flag the risks, then lock. (b) Write the anchor text to match the approved image, never the reverse. (c) A concept must start from the locked pose: Tripura Sundari's arms are already open, so beats like "she opens her arms" are impossible for her (that beat was used for Tara). (d) Known open risks in the locked image: a cross-shaped earring on the left ear, hands near the frame edges, a small face in a full-length frame, a glossy 3D look; offer a quick fix pass if it bothers the director.

### Tripura Sundari, anchor image final touch-up (2026-10-08)
- **Shown:** locked v2c portrait.
- **Feedback:** "that thug cross earring needs to go. please take that out and finalize the anchor image".
- **Change made:** two FLUX edit attempts failed (the first removed the earring but also deleted the crescent, brow jewel, nose stud and stars; the second left the cross in place). Fixed with a small feathered hair-colour patch over the cross (ffmpeg), leaving everything else pixel-identical. Final: `anchors/tripura_sundari_portrait_9x16.png` (source `outputs/anchors/tripura_sundari/tripura_sundari_v3c_patched.png`).
- **Rule for next time:** for a tiny stray artifact, patch it locally; whole-image edit models re-render details they were told to keep. Put "no cross-shaped or symbolic earrings" in the portrait prompt up front.

### Tripura Sundari concepts, round 1 (2026-10-08)
- **Shown:** A glance gives life back, B smile enraptures, C born of awareness, D calm after the storm, then merged E/E2 "The Look That Answers".
- **Feedback:** "Your storylines are very, very, very, very lame."
- **What went wrong:** all four were a face-only beat plus a glow. I then applied the feasibility critic's "max 2 movers" literally and merged down to a smile and a glow, which is the generic motion rejected for Tara. Feasibility was allowed to veto ambition.
- **Rule for next time:** a concept needs a dramatic event with a visible cause and effect in the world, not an expression change. Feasibility critic is advisory; test bold ideas with a cheap 480p draft instead of simplifying them away. Score virality and ambition first; reject any concept whose whole payoff is "she smiles and glows".

### Workflow change: scene-first, no anchors (2026-10-08)
- **Shown:** Bala chariot still made straight from the locked portrait plus a one-paragraph description.
- **Feedback:** "I think we don't even need anchors at this point because you can just create, based on a description, imagery and generate a video scene. Looking at this whole concept incorrectly and kind of inefficiently."
- **Change made:** the working flow is now: scene description -> keyframe images (FLUX, the deity's reference portrait passed as an input reference for identity) -> video model with start/end frames -> review. Anchor JSON and compiled prompts are no longer the gate.
- **Rule for next time:** start from the scene and the imagery, look at frames early, and spend on keyframes (cents) before video (dollars). Keep the reference portrait for identity; do not write per-shot guard-checked prompt pipelines first.

### Cost and autonomy rules (2026-10-08)
- **Feedback:** "if I have to approve and redirect every single time... how annoyingly irritating it is and how expensive it is" and "I want each final output that I post on Instagram to cost me $2 or less."
- **Rule for next time:** generate a large pool of concepts, rank them myself, render only the winners; each posted video costs at most $2 all-in. Choose models by price per clip; pause only when a cap is hit.

### Scene-first batch 1 results (2026-10-08)
- **Process:** 310 pitches (5 angles x ~60) -> 5 virality critics, top 8 each -> I picked 6 for variety/renderability -> FLUX keyframes (start+end, portrait as reference, about $0.05 each) -> Kling 3.0 Std 720p, 10s, start+end frame.
- **Model facts (verified):** Kling 3.0 Std (`kwaivgi/kling-v3.0-std`) accepted the photoreal portrait keyframes and rendered all 6 at about $0.84 per 10s clip; start+end frames gave clean transformations. Seedance 2.0 (fast) and Veo 3.1 Fast REJECTED the keyframes ("may contain real person" / Vertex usage guidelines). Cost per post: about $0.94 including keyframes, under the $2 cap.
- **Quality rank:** meteors-to-petals and lotus dominoes (excellent), crown-becomes-bow, sea-bows, ash revival (good), bow-draws-ocean (weaker: ocean wall read as waterfalls).
- **Rule for next time:** generate start+end keyframes first, check them on a contact sheet, then render on Kling 3.0 Std. Transformation scenes with a clear start state and end state work; "wall of water splitting" is the weakest kind.
- **Director verdict on batch 1:** "this is what I am talking about." Confirmed workflow for every deity: big pitch pool -> critic ranking -> start/end keyframes from the reference portrait -> Kling 3.0 Std 720p at about $0.94 per post, no per-step approvals.
