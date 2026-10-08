# What Seedance 2.5 image-to-video renders reliably

Built from vendor and blog guides and one technical report (no official ByteDance guide found; several details come from Seedance 2.0 tests). Treat as directional and verify with a cheap test.

## Reliable (design concepts around these)
- **One intentional change per clip.** Subtle motion beats many simultaneous changes.
- **Camera moves, not object moves.** A slow push-in is the dependable choice; let the camera create the motion.
- **Faces and micro-expressions**, staged simply with a locked or slowly pushing camera: a slow blink, a gaze settling on the viewer, a faint change of expression. Waist-up framing keeps identity stable.
- **Lighting carried from the source image**, and gentle environmental motion in the background (twinkling stars, drifting mist, a slow sky).
- **A small head turn, gaze shift or slow lean toward the camera** (a restrained turn looks more natural than changing eyes, mouth and pose at once), and a **slow step forward** (our Kali render did this well).
- **Clothing, jewelry and hair settling** with small, natural movement.

## Risky (avoid)
- **Hands and fingers**, especially raised, rotating or holding objects (extra or fused fingers).
- **Water and fluids**, reflections, splashes, "calming" or "flattening" liquid (physics breaks, reflections regenerate independently).
- **Many moving elements**, small tracked objects, objects entering or appearing from nowhere, sequential effects ("one by one").
- **Dense glow and particle effects** (flicker and shimmer), and anything needing on-screen text.
- **Large pose changes**, full-body motion, and reliance on second-by-second timing (the clip is one continuous render).
- **Identity drift** grows with long clips and big motion; keep the face stable and the action restrained.

## Sources
- [Seedance 2.5 image-to-video guide (seedance.tv)](https://www.seedance.tv/blog/seedance-2-5-image-to-video-guide-2026)
- [Seedance 2.5 micro-expressions (weshop.ai)](https://www.weshop.ai/solutions/models/seedance-2-5-micro-expressions-can-an-ai-face-feel-real)
- [Seedance 2.0 image-to-video consistency guide (anikuku)](https://anikuku.com/blog/seedance-2-image-to-video-consistency-guide-2026)
- [Image-to-video prompts guide (Luma)](https://lumalabs.ai/news/image-video-prompts)
- [Image-to-video AI prompts guide (Renderforest)](https://www.renderforest.com/blog/image-to-video-ai-prompts)
- [AI video generator limitations 2026 (is4.ai)](https://is4.ai/blog/our-blog-1/ai-video-generators-limitations-2026-398)
- [Motif-Video 2B technical report](https://arxiv.org/pdf/2604.16503)

## Verified in this project (real renders; these override guesses above)
- **Kali, 10 s, 720p, Seedance 2.5 via OpenRouter (approved by the director):** started on the face from the reference portrait at eye level, eye-level pull-back to full length, then a slow walk toward the viewer with natural arm swing, bare feet on plain dark earth, hair settling. **Walking toward the camera, arm swing and the pull-back all rendered well.**
- **Tara, first render:** standing planted with a raised hand rendered without artifacts, but the beat had no purpose. **Hair moved far too much when the prompt said sea breeze or drifting**: use only "settles under natural gravity".
