"""Reflection storage - stores human reflections on flukes and fragments."""

import json
import os
import uuid
from datetime import datetime, timezone

from app.models import Reflection, ReflectionCreate


class ReflectionStore:
    """Simple file-based reflection storage."""

    def __init__(self, storage_path: str = "./reflections.json") -> None:
        self.storage_path = storage_path
        self.reflections: list[dict[str, object]] = []
        self._load()

    def _load(self) -> None:
        """Load reflections from disk."""
        if os.path.exists(self.storage_path):
            with open(self.storage_path, "r") as f:
                self.reflections = json.load(f)

    def _save(self) -> None:
        """Persist reflections to disk."""
        with open(self.storage_path, "w") as f:
            json.dump(self.reflections, f, indent=2)

    def add_reflection(self, reflection: ReflectionCreate) -> Reflection:
        """Add a new reflection."""
        reflection_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc).isoformat()

        data = {
            "id": reflection_id,
            "text": reflection.text,
            "linked_fragment_ids": reflection.linked_fragment_ids,
            "linked_fluke_tension": reflection.linked_fluke_tension,
            "timestamp": timestamp,
        }

        self.reflections.append(data)
        self._save()

        return Reflection(**data)

    def get_all_reflections(self, limit: int = 100, offset: int = 0) -> list[Reflection]:
        """Get all reflections with pagination."""
        sliced = self.reflections[offset : offset + limit]
        return [Reflection(**r) for r in sliced]

    def get_reflection(self, reflection_id: str) -> Reflection | None:
        """Get a single reflection by ID."""
        for r in self.reflections:
            if r["id"] == reflection_id:
                return Reflection(**r)
        return None

    def count(self) -> int:
        """Return total number of reflections."""
        return len(self.reflections)

    def delete_reflection(self, reflection_id: str) -> bool:
        """Delete a reflection by ID."""
        for i, r in enumerate(self.reflections):
            if r["id"] == reflection_id:
                self.reflections.pop(i)
                self._save()
                return True
        return False
