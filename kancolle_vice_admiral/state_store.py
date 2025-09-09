"""
Simple JSON-backed state store for target knowledge.

Stores per-screen targets with centers in canvas coordinates and a last_seen timestamp.
"""

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional


class StateStore:
    def __init__(self, path: Path):
        self.path = path
        self._data: Dict[str, Any] = {}
        self._loaded = False

    def load(self) -> None:
        if self._loaded:
            return
        if self.path.exists():
            try:
                self._data = json.loads(self.path.read_text(encoding="utf-8"))
            except Exception:
                self._data = {}
        else:
            self._data = {}
        self._loaded = True

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self._data, ensure_ascii=False, indent=2), encoding="utf-8")

    def upsert_target(self, screen_id: str, name: str, cx: float, cy: float, radius: float = 16.0) -> None:
        self.load()
        entry = {
            "name": name,
            "center_canvas": [cx, cy],
            "radius": radius,
            "last_seen": int(time.time()),
        }
        targets: List[Dict[str, Any]] = self._data.get(screen_id, {}).get("targets", [])
        # Replace if exists, else append
        replaced = False
        for t in targets:
            if t.get("name") == name:
                t.update(entry)
                replaced = True
                break
        if not replaced:
            targets.append(entry)
        self._data.setdefault(screen_id, {})["targets"] = targets
        self.save()

    def find_target(self, screen_id: str, name: str) -> Optional[Dict[str, Any]]:
        self.load()
        targets: List[Dict[str, Any]] = self._data.get(screen_id, {}).get("targets", [])
        for t in sorted(targets, key=lambda r: r.get("last_seen", 0), reverse=True):
            if t.get("name") == name:
                return t
        return None


