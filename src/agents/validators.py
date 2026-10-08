"""Pre-Render Validation Council: deterministic guards that audit a composed prompt before any paid render."""

import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Finding:
    level: str  # "error" blocks the render, "warn" does not
    rule: str
    message: str


@dataclass
class Report:
    guard: str
    findings: list[Finding] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not any(f.level == "error" for f in self.findings)

    def error(self, rule: str, message: str) -> None:
        self.findings.append(Finding("error", rule, message))


def _hits(pattern: str, text: str) -> list[str]:
    return sorted({m.group(0).lower() for m in re.finditer(pattern, text, re.IGNORECASE)})


class SemanticGuard:
    """Keeps daylight, occult symbols and trigger words out of the positive prompt and caps the negatives."""

    MAX_NEGATIVES = 6
    DAYLIGHT = r"\b(day\s?light|daytime|sunlight|sunny|bright sky|midday)\b"
    OCCULT = (r"\b(occult|pentagrams?|hexagrams?|sigils?|runes?|satanic|summoning|"
              r"chalk (?:circles?|drawings?)|ritual (?:circles?|stars?)|geometric (?:symbols?|overlays?))\b")
    TRIGGER = r"\b(sacred\w*|mystic\w*)\b"
    # Sanskrit/Hindi loanwords and transliterations are kept out of prompts; plain English descriptions only.
    NON_ENGLISH = r"\b(dhoti|sari|saree|mudra|yantra|yoni|tilak|bindi|kajal|abhaya|varada|mahavidya\w*)\b|[^\x00-\x7f]"

    def check(self, prompt: str, negatives: list[str], excluded: Optional[list[str]] = None) -> Report:
        r = Report("SemanticGuard")
        for rule, pattern in (("daylight", self.DAYLIGHT), ("occult-symbol", self.OCCULT), ("trigger-word", self.TRIGGER)):
            if hits := _hits(pattern, prompt):
                r.error(rule, f"forbidden in prompt: {', '.join(hits)}")
        if hits := _hits(self.NON_ENGLISH, prompt + " " + " ".join(negatives)):
            r.error("non-english", f"use plain English instead of: {', '.join(hits)}")
        for word in excluded or []:
            if hits := _hits(rf"\b{re.escape(word)}\w*", prompt):
                r.error("excluded", f"anchor excludes '{word}' but the prompt mentions: {', '.join(hits)}")
        terms = [n.strip() for n in negatives if n.strip()]
        if len(terms) > self.MAX_NEGATIVES:
            r.error("negative-cap", f"{len(terms)} negative terms; the limit is {self.MAX_NEGATIVES}")
        if hits := _hits(self.TRIGGER, " ".join(terms)):
            r.error("trigger-word", f"forbidden in negatives: {', '.join(hits)}")
        return r


class MotionGuard:
    """Audits motion text for contradictions: abrupt cuts, hair state jumps, non-physical hair, broken shot timing."""

    ABRUPT = r"\b(jump cuts?|hard cuts?|smash cuts?|cuts? to|snaps?|instantly|suddenly|teleport\w*|pops? into)\b"
    HAIR = r"\b(hair|mane)\b"
    HAIR_GRADUAL = r"\b(gradual\w*|settl\w*|cascad\w*|sway\w*|billow\w*)\b"
    HAIR_BAD = r"\b(stiff|frozen|rigid|floating|gravity-defying)\s+(hair|mane)\b"
    HAIR_JUMP = r"\b(combed|ties?|tied|braid(?:s|ed)?|bun)\b"  # "unbraided" does not match
    LOW_ANGLE = r"\b(low[- ]angle|upward tilt|nostril)\b"
    SHOT = re.compile(r"Shot (\d+) \((\d+)-(\d+)s\)")

    def check(self, prompt: str) -> Report:
        r = Report("MotionGuard")
        if hits := _hits(self.ABRUPT, prompt):
            r.error("abrupt-transition", f"abrupt motion or cut language: {', '.join(hits)}")
        if re.search(self.HAIR, prompt, re.IGNORECASE):
            if not re.search(self.HAIR_GRADUAL, prompt, re.IGNORECASE):
                r.error("hair-physics", "hair is described without gradual settling, swaying or billowing")
            if hits := _hits(self.HAIR_BAD, prompt):
                r.error("hair-physics", f"non-physical hair: {', '.join(hits)}")
            if hits := _hits(self.HAIR_JUMP, prompt):
                r.error("hair-continuity", f"hair state changes mid-clip: {', '.join(hits)}")
        if re.search(r"eye level", prompt, re.IGNORECASE) and (hits := _hits(self.LOW_ANGLE, prompt)):
            r.error("camera-contradiction", f"eye-level camera conflicts with: {', '.join(hits)}")
        shots = [tuple(map(int, m.groups())) for m in self.SHOT.finditer(prompt)]
        end = 0
        for n, start, stop in shots:
            if start != end or stop <= start:
                r.error("shot-timing", f"Shot {n} spans {start}-{stop}s but should start at {end}s (gap, overlap or jump cut)")
            end = stop
        return r
