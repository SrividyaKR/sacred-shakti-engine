"""Series Showrunner: tracks the order and status of the ten Mahavidyas in configs/series_manifest.json."""

import copy
import json
from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel

ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = ROOT / "configs" / "series_manifest.json"

Status = Literal["queued", "active", "completed"]


class Deity(BaseModel):
    order: int
    id: str
    status: Status
    anchor_locked: bool


class Showrunner:
    def __init__(self, path: Path = MANIFEST_PATH):
        self.path = path
        self._raw = json.loads(path.read_text(encoding="utf-8"))
        self.deities = sorted((Deity(**d) for d in self._raw["deities"]), key=lambda d: d.order)

    def get(self, deity_id: str) -> Deity:
        for d in self.deities:
            if d.id == deity_id:
                return d
        raise KeyError(f"'{deity_id}' is not in the series manifest ({[d.id for d in self.deities]})")

    def active(self) -> Optional[Deity]:
        return next((d for d in self.deities if d.status == "active"), None)

    def current(self) -> Optional[Deity]:
        """The deity to work on: the active one, else the first queued. None when the series is complete."""
        return self.active() or next((d for d in self.deities if d.status == "queued"), None)

    def set_status(self, deity_id: str, status: Status) -> None:
        self.get(deity_id).status = status
        self.save()

    def advance(self, write: bool = True) -> Optional[Deity]:
        """Complete the active deity (if any) and activate the next queued one. Returns the newly active deity.

        With write=False nothing is changed or saved; the result is only a preview."""
        deities = self.deities if write else copy.deepcopy(self.deities)
        for d in deities:
            if d.status == "active":
                d.status = "completed"
        nxt = next((d for d in deities if d.status == "queued"), None)
        if nxt:
            nxt.status = "active"
        if write:
            self.save()
        return nxt

    def save(self) -> None:
        self._raw["deities"] = [d.model_dump() for d in self.deities]
        self.path.write_text(json.dumps(self._raw, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
