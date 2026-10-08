"""Director Agent: turns a canonical character anchor into a motion/cinematography prompt."""

import json
from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[2]
ANCHOR_DIR = ROOT / "configs" / "anchors"


class Appearance(BaseModel):
    skin: str
    eyes: str
    third_eye: str
    headwear: str
    hair: str
    attire: list[str]
    ornamentation: list[str] = Field(default_factory=list)
    feet: str


class Environment(BaseModel):
    sky: str
    lighting: str
    ground: str
    excluded: list[str] = Field(default_factory=list)  # words the Semantic Guard keeps out of the prompt


MotionArchetype = Literal["grounded_stride", "stationary_command", "atmospheric_arc"]


class CreativePalette(BaseModel):
    elemental_domain: str  # the natural element or setting that shapes the scene's physics
    motion_archetype: MotionArchetype  # how the figure and camera move after the opening pull-back
    signature_phenomena: list[str]  # physical dynamics unique to this deity, written as things to show


class Shot(BaseModel):
    duration: int
    camera: str
    action: str


class Anchor(BaseModel):
    id: str
    name: str
    epithet: str
    anchor_locked: bool = False  # True only after a human approves the reference portrait
    reference_images: dict[str, str]
    appearance: Appearance
    environment: Environment
    creative_palette: Optional[CreativePalette] = None  # None keeps the legacy grounded_stride plan (Kali)
    negatives: list[str]
    shots: list[Shot] = Field(default_factory=list)  # optional override of the default shot plan


class PromptBundle(BaseModel):
    character: str
    prompt: str
    negatives: list[str]
    shots: list[Shot]
    duration: int
    reference_image: Optional[str]


OPENING_CAMERA = ("Starts on the face from the reference portrait at horizontal eye level, then a smooth, continuous "
                  "optical pull-back locked at eye level reveals Her full length. The crown and silver crescent moon "
                  "stay centered and fully framed.")
SETTLE = "Her hair gradually settles under natural gravity, cascading down past Her shoulders."

# One shot plan per motion archetype. grounded_stride is the plan locked from the approved Kali render.
SHOT_PLANS = {
    "grounded_stride": [
        Shot(duration=5, camera=OPENING_CAMERA, action=f"As the camera pulls back and She begins Her stride, {SETTLE}"),
        Shot(
            duration=5,
            camera="The full-length figure stays framed at eye level.",
            action=("She walks forward toward the viewer with majestic, sovereign grace. Her arms swing casually and "
                    "naturally at Her sides in rhythm with Her steps, and Her hair billows softly with the cadence of "
                    "Her steps. Bare feet step forward onto {ground}."),
        ),
    ],
    "stationary_command": [
        Shot(duration=5, camera=OPENING_CAMERA, action=f"As the camera pulls back, {SETTLE}"),
        Shot(
            duration=5,
            camera="The full-length figure stays framed at eye level while the camera holds steady.",
            action=("She stands planted on {ground}, bare feet firm, radiating sovereign command, chest expanded and "
                    "gaze steady toward the viewer."),
        ),
    ],
    "atmospheric_arc": [
        Shot(duration=5, camera=OPENING_CAMERA, action=f"As the camera pulls back, {SETTLE}"),
        Shot(
            duration=5,
            camera=("The camera glides in a slow, smooth arc at eye level around the figure, keeping the crown "
                    "centered and fully framed."),
            action="She stands composed and sovereign while the surroundings move around Her.",
        ),
    ],
}
DEFAULT_SHOTS = SHOT_PLANS["grounded_stride"]


class Director:
    def __init__(self, anchor_dir: Path = ANCHOR_DIR):
        self.anchor_dir = anchor_dir

    def load_anchor(self, character_id: str) -> Anchor:
        path = self.anchor_dir / f"{character_id}.json"
        if not path.exists():
            raise FileNotFoundError(f"No anchor definition for '{character_id}' at {path.relative_to(ROOT)}")
        return Anchor(**json.loads(path.read_text(encoding="utf-8")))

    def compose(self, character_id: str, aspect: str = "portrait_9x16") -> PromptBundle:
        return self.compose_anchor(self.load_anchor(character_id), aspect)

    def compose_portrait(self, a: Anchor) -> str:
        """Still-image prompt for the reference portrait that becomes the video's first frame."""
        ap, env = a.appearance, a.environment
        return " ".join([
            f"Cinematic photorealistic portrait of {a.name}, {a.epithet}, the Hindu goddess.",
            "Framing: head and upper chest, front-facing, camera at horizontal eye level, "
            "crown fully framed and centered, vertical 9:16 composition.",
            f"Complexion: {ap.skin}. Eyes: {ap.eyes}. Forehead: {ap.third_eye}.",
            f"Crown: {ap.headwear}.",
            f"Hair: {ap.hair}.",
            f"Attire: {'; '.join(ap.attire)}.",
            *([f"Ornamentation: {'; '.join(ap.ornamentation)}."] if ap.ornamentation else []),
            f"Background: {env.sky}.",
            f"Lighting: {env.lighting}.",
            "Style: reverent, elegant, non-graphic, finely detailed, calm sovereign expression.",
        ])

    def compose_anchor(self, a: Anchor, aspect: str = "portrait_9x16") -> PromptBundle:
        ap, env = a.appearance, a.environment
        palette = a.creative_palette
        plan = a.shots or SHOT_PLANS[palette.motion_archetype if palette else "grounded_stride"]
        shots = [sh.model_copy(update={"camera": sh.camera.format(ground=env.ground),
                                       "action": sh.action.format(ground=env.ground)}) for sh in plan]

        t, timeline = 0, []
        for i, sh in enumerate(shots, 1):
            timeline.append(f"Shot {i} ({t}-{t + sh.duration}s): {sh.camera} {sh.action}")
            t += sh.duration

        prompt = " ".join([
            f"{a.name}, {a.epithet}, the Hindu goddess, matching the reference portrait exactly.",
            f"Complexion: {ap.skin}. Eyes: {ap.eyes}. Forehead: {ap.third_eye}.",
            f"Crown: {ap.headwear}.",
            f"Hair: {ap.hair}.",
            f"Attire: {'; '.join(ap.attire)}.",
            *([f"Ornamentation: {'; '.join(ap.ornamentation)}."] if ap.ornamentation else []),
            f"{ap.feet.capitalize()}.",
            f"Setting: {env.sky}; the ground is {env.ground}.",
            *([f"Elemental domain: {palette.elemental_domain}."] if palette else []),
            f"Lighting: {env.lighting}.",
            *timeline,
            *([f"Physical dynamics throughout: {'; '.join(palette.signature_phenomena)}."] if palette else []),
            "Style: reverent cinematic realism, elegant and non-graphic, smooth natural motion, "
            "consistent identity and costume throughout.",
        ])
        return PromptBundle(
            character=a.id, prompt=prompt, negatives=a.negatives, shots=shots, duration=t,
            reference_image=a.reference_images.get(aspect),
        )
