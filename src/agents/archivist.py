"""Iconography Archivist: turns a deity's classical iconography into a strict, English-only anchor definition.

    .venv/bin/python -m src.agents.archivist tara [--dry-run] [--force]
"""

import argparse
import json
import re
import sys
from pathlib import Path

from src.agents.director import Anchor, Director
from src.agents.showrunner import Showrunner
from src.agents.validators import MotionGuard, SemanticGuard

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "configs" / "mahavidyas.json"
ANCHOR_DIR = ROOT / "configs" / "anchors"
NEGATIVE_COUNT = 6  # the anchor schema carries exactly six negatives

# Classical terms and their plain-English replacements. Applied to every string before validation.
GLOSSARY = {
    r"\bkartari\b": "scissors", r"\bkapala\b": "skull cup", r"\bkhadga\b": "sword", r"\bjata\b": "matted locks",
    r"\bdhoti\b": "pleated wrap skirt", r"\bsaree\b|\bsari\b": "draped silk", r"\bmudras?\b": "hand gesture",
    r"\byantra\b": "geometric diagram", r"\bbindi\b|\btilak\b": "forehead mark", r"\bveena\b": "stringed instrument",
}

# Curated visual canon, written in plain English from the classical iconography. Review before locking an anchor.
CANON = {
    "tripura_sundari": {
        "crown_ornament": "jeweled crescent moon",
        "first_frame": "a front-facing, full-length portrait of Tripura Sundari at eye level, seated cross-legged on a golden lotus throne above calm dark water, both arms open to the sides with palms up, a tall jeweled crown with a crescent moon centered and fully framed, a gentle faint smile, a deep blue twilight sky fading to soft pink behind Her, and nothing else in the frame.",
        "appearance": {
            "skin": "warm golden-peach skin with a soft glow",
            "eyes": "large, warm, luminous eyes full of compassion",
            "third_eye": "a small jeweled mark at the brow",
            "headwear": "tall tiered gold crown set with rubies and pearls, topped with a jeweled crescent moon on a pearl finial",
            "hair": "long, wavy dark hair falling over the shoulders",
            "attire": [
                "draped crimson silk bodice and shoulder wrap with a wide gold border",
                "crimson silk trousers gathered at the ankles, with a gold-bordered drape across the lap"
            ],
            "ornamentation": [
                "multi-strand pearl necklaces with ruby pendants",
                "ruby and pearl armbands and stacked gold and ruby bangles",
                "gold waist belt set with rubies and small bells"
            ],
            "feet": "bare feet"
        },
        "creative_palette": {
            "elemental_domain": "calm dark water at twilight, a golden lotus throne, a soft rose glow",
            "motion_archetype": "seated_presence",
            "signature_phenomena": [
                "a soft rose-gold radiance rising slowly from Her form as She smiles",
                "gentle ripples spreading slowly across the calm water around the lotus",
                "a slow, warm smile that brightens Her glow"
            ]
        },
        "environment": {
            "sky": "deep blue twilight sky fading to soft pink at the horizon, with a few faint stars",
            "lighting": "soft twilight light with a gentle rose glow, lighting the face, crown and jewels",
            "ground": "calm dark water with gentle ripples around a golden lotus throne",
            "excluded": [
                "daylight",
                "fire"
            ]
        },
        "negatives": [
            "daylight",
            "bright sky",
            "stiff hair",
            "geometric overlays",
            "low angle shot",
            "modern clothing"
        ]
    },
    "tara": {
        "crown_ornament": "golden sun disc",
        "first_frame": ("a front-facing, three-quarter-length portrait of Tara at eye level, standing in calm shallow dark water: "
                        "crown with a golden sun disc centered and fully framed, a bright star above it, a visible unlit third eye, "
                        "eyes open with a calm expression, a starry midnight sky behind Her, and nothing else in the frame."),
        "appearance": {
            "skin": "deep sapphire-blue skin",
            "eyes": "large, luminous eyes with a steady, compassionate gaze",
            "third_eye": "a subtle vertical third eye",
            "headwear": "elaborate tiered gold and silver crown resting flush on voluminous black hair, topped with a golden sun disc at its peak, with a bright guiding star above",
            "hair": "thick, long black hair in heavy locks falling past the shoulders",
            "attire": [
                "dark indigo fitted V-neck silk bodice with subtle embroidered silver starbursts",
                "fitted pleated wrap skirt in a tiger-skin pattern of gold and black stripes",
            ],
            "ornamentation": [
                "multi-layered skull garland with a silver star pendant",
                "ornate serpent-shaped gold armbands and wrist cuffs on both arms",
                "gold waist belt with a silver star medallion",
            ],
            "feet": "bare feet",
        },
        "creative_palette": {
            "elemental_domain": "reflective dark ocean shore, distant starlight, solitary guiding star",
            "motion_archetype": "stationary_command",
            "signature_phenomena": [
                "She slowly extends Her open hand over the dark water, and a narrow path of starlight spreads across the surface toward the viewer, guiding the way across",
                "soft concentric ripples spreading outward from the path of starlight on the calm dark water",
                "heavy black hair settling under natural gravity, with only a slight sway from Her motion",
            ],
        },
        "environment": {
            "sky": "deep indigo midnight sky with one bright guiding star and cold distant stars",
            "lighting": "low-key moonlit lighting; cool blue-white gleams catch the silhouette, crown and silver jewelry",
            "ground": "calm shallow dark water at the edge of a black ocean",
            "excluded": ["daylight", "fire"],
        },
        "negatives": ["daylight", "bright sky", "stiff hair", "geometric overlays", "low angle shot", "modern clothing"],
    },
}


class ArchivistError(Exception):
    pass


def to_english(value):
    """Replace glossary terms, drop leftover parenthetical glosses, and normalise whitespace (recursive)."""
    if isinstance(value, list):
        return [to_english(v) for v in value]
    if isinstance(value, dict):
        return {k: to_english(v) for k, v in value.items()}
    if not isinstance(value, str):
        return value
    for pattern, english in GLOSSARY.items():
        value = re.sub(pattern, english, value, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", re.sub(r"\s*\([^)]*\)", "", value)).strip()


class Archivist:
    def build(self, deity_id: str) -> tuple[Anchor, list[str]]:
        """Return the anchor and notes about classical elements that were deliberately not encoded."""
        Showrunner().get(deity_id)  # must be in the series manifest
        if deity_id not in CANON:
            raise ArchivistError(f"No visual canon authored for '{deity_id}' yet; add it to CANON in archivist.py")
        entry = next((m for m in json.loads(CONFIG_PATH.read_text(encoding="utf-8"))["mahavidyas"] if m["id"] == deity_id), None)
        if entry is None:
            raise ArchivistError(f"'{deity_id}' is missing from configs/mahavidyas.json")

        canon = to_english(CANON[deity_id])
        anchor = Anchor(
            id=deity_id,
            name=entry["name"],
            epithet=to_english(entry["epithet"]),
            anchor_locked=False,
            reference_images={
                "portrait_9x16": f"anchors/{deity_id}_portrait_9x16.png",
                "profile_1x1": f"anchors/{deity_id}_profile_1x1.png",
            },
            **canon,
        )
        held = to_english(entry["iconography"]["attributes"])
        notes = [f"Held attributes not encoded (the shot plan has free-swinging arms): {', '.join(held)}"]
        self.validate(anchor)
        return anchor, notes

    def validate(self, anchor: Anchor) -> None:
        problems = []
        if anchor.creative_palette is None or not anchor.creative_palette.signature_phenomena:
            problems.append("creative_palette with at least one signature phenomenon is required")
        if len(anchor.negatives) != NEGATIVE_COUNT:
            problems.append(f"expected exactly {NEGATIVE_COUNT} negatives, got {len(anchor.negatives)}")
        bundle = Director().compose_anchor(anchor)
        texts = [bundle.prompt, Director().compose_portrait(anchor)]
        for text in texts:
            for rep in (SemanticGuard().check(text, anchor.negatives, anchor.environment.excluded),):
                problems += [f"{rep.guard} {f.rule}: {f.message}" for f in rep.findings]
        rep = MotionGuard().check(bundle.prompt)
        problems += [f"{rep.guard} {f.rule}: {f.message}" for f in rep.findings]
        if problems:
            raise ArchivistError("anchor failed validation:\n  " + "\n  ".join(dict.fromkeys(problems)))

    def write(self, anchor: Anchor, force: bool = False) -> Path:
        path = ANCHOR_DIR / f"{anchor.id}.json"
        if path.exists() and json.loads(path.read_text(encoding="utf-8")).get("anchor_locked") and not force:
            raise ArchivistError(f"{path.relative_to(ROOT)} is locked; pass --force to overwrite")
        path.write_text(json.dumps(anchor.model_dump(exclude={"shots"}), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return path


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("deity_id")
    ap.add_argument("--dry-run", action="store_true", help="print the anchor without writing it")
    ap.add_argument("--force", action="store_true", help="overwrite a locked anchor")
    args = ap.parse_args()
    archivist = Archivist()
    try:
        anchor, notes = archivist.build(args.deity_id)
        text = json.dumps(anchor.model_dump(exclude={"shots"}), indent=2, ensure_ascii=False)
        if args.dry_run:
            print(text)
        else:
            print(f"Wrote {archivist.write(anchor, args.force).relative_to(ROOT)} (anchor_locked: false)")
    except (ArchivistError, KeyError) as e:
        print(f"Archivist: {e}", file=sys.stderr)
        return 1
    for n in notes:
        print(f"note: {n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
