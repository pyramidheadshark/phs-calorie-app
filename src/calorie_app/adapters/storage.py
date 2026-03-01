from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path

from calorie_app.config import settings


class PhotoStorage:
    def __init__(self) -> None:
        self._base_path = Path(settings.photo_storage_path)
        self._base_path.mkdir(parents=True, exist_ok=True)

    def save(self, image_bytes: bytes, ext: str = "jpg") -> str:
        filename = f"{uuid.uuid4()}.{ext}"
        path = self._base_path / filename
        path.write_bytes(image_bytes)
        return str(path)

    def delete(self, path: str) -> None:
        p = Path(path)
        if p.exists():
            p.unlink()

    def cleanup_old(self, max_age_hours: int | None = None) -> int:
        hours = max_age_hours or settings.photo_max_age_hours
        now = datetime.now(timezone.utc)
        deleted = 0
        for f in self._base_path.glob("*.jpg"):
            age_hours = (now.timestamp() - f.stat().st_mtime) / 3600
            if age_hours > hours:
                f.unlink()
                deleted += 1
        for f in self._base_path.glob("*.png"):
            age_hours = (now.timestamp() - f.stat().st_mtime) / 3600
            if age_hours > hours:
                f.unlink()
                deleted += 1
        return deleted

    def get_bytes(self, path: str) -> bytes | None:
        p = Path(path)
        if p.exists():
            return p.read_bytes()
        return None


photo_storage = PhotoStorage()
