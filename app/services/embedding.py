from __future__ import annotations

import hashlib
from functools import lru_cache

from app.core.config import get_settings

settings = get_settings()


class EmbeddingService:
    """Central embedding gateway.

    Production uses a local BGE model through sentence-transformers. The hash
    embedding remains available only as a fallback for tests or constrained
    demo environments.
    """

    def __init__(self) -> None:
        self.settings = get_settings()

    @property
    def model_name(self) -> str:
        if self.settings.embedding_provider.lower() == "bge":
            return "bge-m3"
        return "hash-demo"

    def embed_text(self, text: str) -> list[float]:
        vectors = self.embed_texts([text])
        return vectors[0] if vectors else [0.0] * self.settings.embedding_dimension

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        cleaned = [text or "" for text in texts]
        if not cleaned:
            return []

        if self.settings.embedding_provider.lower() in {"fake", "hash", "demo"}:
            return [fake_embedding(text, self.settings.embedding_dimension) for text in cleaned]

        model = _load_sentence_transformer(
            self.settings.embedding_model_path,
            self.settings.embedding_device,
        )
        encoded = model.encode(
            cleaned,
            batch_size=self.settings.embedding_batch_size,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        vectors = encoded.tolist() if hasattr(encoded, "tolist") else encoded
        return [_fit_dimension([float(value) for value in vector], self.settings.embedding_dimension) for vector in vectors]


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


@lru_cache(maxsize=2)
def _load_sentence_transformer(model_path: str, device: str):
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        raise RuntimeError(
            "当前配置启用了真实语义向量，但缺少 sentence-transformers。"
            "请先执行：pip install sentence-transformers，或将 EMBEDDING_PROVIDER 设置为 fake。"
        ) from exc

    return SentenceTransformer(model_path, device=device)


def _fit_dimension(vector: list[float], dimension: int) -> list[float]:
    if len(vector) == dimension:
        return vector
    if len(vector) > dimension:
        return vector[:dimension]
    return vector + [0.0] * (dimension - len(vector))


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
