# Video model survey (2026-10-08)

Scope: i2v, 9:16, 10 s, goddess on a lotus above water at twilight. Web sources are mostly vendor blogs and aggregators; they disagree and give little rigorous VFX testing. Items marked **UNVERIFIED** could not be confirmed.

## Sources
- VideoGen model roundup (vendor, editorial): https://videogen.io/best-ai-video-models
- Roundup search (Invideo, Higgsfield, Atlas Cloud, imagine.art, Pixazo, media.io): https://invideo.io/blog/best-ai-video-generation-models/ , https://www.atlascloud.ai/blog/tips/best-ai-video-generation-models-2026
- OpenRouter video docs: https://openrouter.ai/docs/guides/overview/multimodal/video-generation (live list: `GET https://openrouter.ai/api/v1/videos/models`)
- Seedance 2.0 prompt guide: https://www.rundiffusion.com/seedance-2-0-prompt-guide
- Seedance 2.5 i2v (Runware): https://runware.ai/docs/models/bytedance-seedance-2-5/guides/image-to-video.md
- Seedance first/last frame: https://www.seedance.tv/blog/seedance-first-and-last-frame
- Kling start/end frames: https://kling.ai/quickstart/ai-video-start-end-frames
- Kling 3.0 vs Veo 3.1: https://magichour.ai/blog/kling-30-vs-veo-31
- Disintegration/dissolve effects: https://pexo.ai/gallery/disintegration-effect-video
- Flower bloom keyframe case study: https://alici.ai/formulas/media/aida-ai-pro/a92dffad-39b3-5151-8bc6-c534839448eb-ethereal-teal-flower-bloom-ai-video-aida-ai-pro

## Model table
Prices are per second, derived from aggregator per-minute figures unless noted. Treat as indicative.

| Model | Strengths | Weaknesses | OpenRouter id | Price / max |
|---|---|---|---|---|
| Seedance 2.5 (ByteDance) | Best prompt adherence and reference conditioning (up to 50 multimodal refs per VideoGen), localized edits, native audio, first/last frame | Few public benchmarks; rolling access. Seedance 2.0 guide says it is best for scenes/architecture, and suggests Kling/Veo for people; realistic real faces blocked | Used by this project already (id not re-verified today) | 720p, up to 30 s (VideoGen). Seedance 2.0: ~$0.15/s 720p, up to 4K/15 s |
| Kling v3 / 3.0 | Fast motion, physics-based transitions (vendor claim), up to 6 camera cuts, 4K/60fps, start+end frames | Pricey (~$0.34/s 1080p Pro); more reference drift under aggressive motion; artifacts in complex camera moves | Not seen on OpenRouter (UNVERIFIED) | 4K, 15 s |
| Veo 3.1 (Google) | Natural physics, water and environmental effects, realism, audio, reference images for characters, scene extension | Costly; 8 s base clips; needs detailed prompts | `google/veo-3.1` (OpenRouter docs): 4/6/8 s, 720p/1080p, 9:16 ok, ~$0.50/s, $0.75/s at 1080p (docs example; confirm live). Fast ~$0.15, Lite ~$0.08 elsewhere | 8 s max, extendable |
| Sora 2 (OpenAI) | Cinematic realism, narrative scenes | Thin 2026 coverage; 10 s, no native audio per one source | Not seen (UNVERIFIED) | UNVERIFIED |
| Wan 2.7 / 3.0 (Alibaba) | Open weights (Apache 2.0), first/last frame, reference-to-video, 1080p/15 s, strong motion/physics reputation; one source says Wan 3.0 tops the arena | Trails flagships on prompt adherence (VideoGen) | `alibaba/wan-2.7` (docs show `frame_images` and `input_references`) | 1080p/15 s; price UNVERIFIED |
| Hailuo 2.3 / MiniMax H3 | Realistic human motion cheaply; H3 2K, 15 s, multi-reference (up to 9 images), ~$0.13/s | Hailuo 2.3 no audio; duration inconsistent across sources | `minimax/hailuo-3` (docs); 2.3 not seen | H3: 2K/15 s |
| Runway Gen-4.5 | Motion control, editing workflow, physics-heavy scenes | Value mostly in the surrounding tools | Not seen (UNVERIFIED) | UNVERIFIED |
| Gemini Omni Flash (Google) | Top arena Elo in several roundups, conversational editing, audio | 720p/24fps, 10 s, no extension, preview | Not seen (UNVERIFIED) | ~$0.10/s |
| Grok Imagine 1.5 lite (xAI) | Cheapest, i2v, ref images | Lowest Elo, 720p rendering | `x-ai/grok-imagine-video-1.5-lite`, from $0.02/s (OpenRouter page) | 1080p upscaled |
| FLUX 3 (BFL) | Keyframes, continuation, audio | HD native, 20 s | Not seen | UNVERIFIED |
| Luma Ray3 | Photorealism, physics (one mention) | Little data | Not seen | UNVERIFIED |

OpenRouter caveat: my fetch of `/api/v1/models` returned only text LLMs, and the filtered models page showed only one video model (probably truncated). The authoritative list is `GET /api/v1/videos/models` (returns supported durations, resolutions, passthrough params). Run it with the project's key before choosing.

## Capability answers
(a) Large-scale VFX (waves, water, shatter, smoke, structures forming): no head-to-head tests found. Claims: Veo strongest on water/environmental effects and physical realism; Kling v3 for physics-based dissolve/energy ripples; Wan and Runway for physics. Seedance is strong on scenes/architecture and has first/last frame plus reference video for effect transfer. Treat all as unverified until our own tests. The project's `research/seedance_capabilities.md` (verified renders) outranks this survey.
(b) Hand-object interaction: not covered by any source found. **UNVERIFIED**. Kling and Veo are the usual picks for people and hands; test directly.
(c) Identity from a reference image: Seedance (up to 9-50 refs), MiniMax H3 (multi-ref), Veo 3.1 (reference images), Wan 2.7 (reference-to-video). Kling may drift under aggressive motion (one source).

## What viral mythology/devotional AI reels do
Search found little hard evidence (no Reels view data, no named viral accounts); **mostly UNVERIFIED**. What the sources did show:
- Statue-to-human morph reels: strict three-beat formula, static statue, morph, photorealistic human (alici.ai case study, modest views).
- Template-driven mythology videos (script, visuals, voiceover, captions, music) on revid.ai; sample view counts were tiny, so these show the commodity baseline, not what wins.
- General practice recommended in guides: narrative beats (setup, action, tension, resolution), one clean camera move, scale shown by pull-back/rise from a close detail.
Suggested techniques to test, from general knowledge, not sourced: scale reveal by pulling back from the face to the full cosmic setting, a single transformation per clip as the share hook, particle/petal dissolve as the climax, sound design (drum hit, swell) synced to the transformation, seamless loop where the last frame matches the first.

## Prompting techniques for reliable i2v VFX
- Let the image own the look and the prompt own the movement (Seedance 2.0 guide). Keep the camera simple: one move.
- Write the transformation as a timed sequence: opening state, the action, ending state. Name the breakup style, direction and speed ("slow gentle dissolve into golden dust" vs "explosive shatter"); the more specific, the better (Pexo).
- Use waypoints for growth/morph effects: keyframes for each stage (bud, half-bloom, full bloom), via start+end frame or multiple clips (alici.ai).
- Start+end frame (Seedance, Kling, Wan) gives the strongest control over a morph because the model invents only the middle; choose two keyframes that generate cleanly and share an anchor (same horizon, composition, light). Clean first frame reduces drift.
- Water wave guidance (my suggestion, not sourced): state the direction, the crest behaviour ("the crest curls, then breaks into drifting petals"), a locked-off camera, and keep the goddess motion minimal so identity holds.
- Seedance: order the prompt as references, scene, action, camera, timing, audio; label each reference's role; use "one continuous shot with no cuts" for continuity; state what must not change when editing. A reference video can carry an effect or camera path.
- Negatives for artifacts (distorted petals, flicker) are suggested by one source; Seedance via this project has no negative field, so use the "Avoid:" clause.
- Draft at low res first, then render final.

## Recommendation
Both ideas hinge on a single large transformation with the goddess staying consistent, so use start+end frames, not a pure prompt.

1. **Shadow Tide wave shatters into petals**: primary Seedance 2.5 (already integrated, strong reference identity, first/last frame). End frame: the water surface scattered with petals, goddess unchanged. Prompt the crest curling then breaking into drifting petals in sequence. Backup if the particle break-up looks muddy: Veo 3.1 (`google/veo-3.1`, best-cited for water physics; 8 s, so generate 8 s and extend or accept 8 s; cost ~$4-6 per clip) or Kling v3 (physics-based dissolve, not on OpenRouter as far as verified). Test at 480p draft on Seedance first, then one Veo draft for comparison.
2. **Crescent grows to full moon**: Seedance 2.5 with start frame (crescent) and end frame (full moon), possibly a mid keyframe (half moon) as in the bloom case study; slow, steady camera, moon is a simple lit shape so low risk. This is the lowest-risk idea of the two.

Before spending: query `/api/v1/videos/models`, confirm the Seedance 2.5 id and whether `frame_images` (end frame) is supported, and check `research/seedance_capabilities.md`.
