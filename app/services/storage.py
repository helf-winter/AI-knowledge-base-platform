from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import hashlib


@dataclass
class StoredFile:
    file_name: str
    content: bytes
    content_type: str | None = None


def calculate_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def save_local_temp(file_name: str, content: bytes, base_dir: str = "./data/uploads") -> str:
    target_dir = Path(base_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    file_path = target_dir / file_name
    file_path.write_bytes(content)
    return str(file_path.resolve())
