from __future__ import annotations

import hashlib

from app.core.config import get_settings

settings = get_settings()


def fake_embedding(text: str, dimension: int | None = None) -> list[float]:
    dim = dimension or settings.embedding_dimension
    if not text:
        return [0.0] * dim

    digest = hashlib.sha256(text.encode("utf-8", errors="ignore")).digest()
    vector: list[float] = []
    for i in range(dim):
        byte = digest[i % len(digest)]
        vector.append((byte / 255.0) * 2.0 - 1.0)
    return vector


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if len(a) != len(b) or not a:
        return 0.0

    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(y * y for y in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def vector_distance(a: list[float], b: list[float]) -> float:
    """Return a simple cosine distance surrogate used for local demo."""

    return 1.0 - cosine_similarity(a, b)
