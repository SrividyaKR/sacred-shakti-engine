"""Director Agent: turns a canonical character anchor into a motion/cinematography prompt."""

import json
from pathlib import Path
from typing import Optional

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


class Shot(BaseModel):
    duration: int
    camera: str
    action: str


class Anchor(BaseModel):
    id: str
    name: str
    epithet: str
    reference_images: dict[str, str]
    appearance: Appearance
    environment: Environment
    negatives: list[str]
    shots: list[Shot] = Field(default_factory=list)  # optional override of the default shot plan


class PromptBundle(BaseModel):
    character: str
    prompt: str
    negatives: list[str]
    shots: list[Shot]
    duration: int
    reference_image: Optional[str]


# Default plan, locked from the approved Kali render: eye-level pull-back from the face, then a queenly walk.
DEFAULT_SHOTS = [
    Shot(
        duration=5,
        camera=("Starts on the face from the reference portrait at horizontal eye level, then a smooth, continuous "
                "optical pull-back locked at eye level reveals Her full length. The crown and silver crescent moon "
                "stay centered and fully framed."),
        action=("As the camera pulls back and She begins Her stride, Her hair gradually settles under natural "
                "gravity, cascading down past Her shoulders."),
    ),
    Shot(
        duration=5,
        camera="The full-length figure stays framed at eye level.",
        action=("She walks forward toward the viewer with majestic, sovereign grace. Her arms swing casually and "
                "naturally at Her sides in rhythm with Her steps, and Her hair billows softly with the cadence of "
                "Her steps. Bare feet step forward onto plain dark earth."),
    ),
]


class Director:
    def __init__(self, anchor_dir: Path = ANCHOR_DIR):
        self.anchor_dir = anchor_dir

    def load_anchor(self, character_id: str) -> Anchor:
        path = self.anchor_dir / f"{character_id}.json"
        if not path.exists():
            raise FileNotFoundError(f"No anchor definition for '{character_id}' at {path.relative_to(ROOT)}")
        return Anchor(**json.loads(path.read_text(encoding="utf-8")))

    def compose(self, character_id: str, aspect: str = "portrait_9x16") -> PromptBundle:
        a = self.load_anchor(character_id)
        ap, env = a.appearance, a.environment
        shots = a.shots or DEFAULT_SHOTS

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
            f"Lighting: {env.lighting}.",
            *timeline,
            "Style: reverent cinematic realism, elegant and non-graphic, smooth natural motion, "
            "consistent identity and costume throughout.",
        ])
        return PromptBundle(
            character=a.id, prompt=prompt, negatives=a.negatives, shots=shots, duration=t,
            reference_image=a.reference_images.get(aspect),
        )
