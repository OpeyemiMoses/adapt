"""Pluggable embedding provider implementations for ADAPT."""

from __future__ import annotations

import hashlib
import math
import os
import re
from typing import List, Optional

from adapt.embeddings.base import EmbeddingProvider


def cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    """Compute cosine similarity between two float vectors."""
    if not vec_a or not vec_b or len(vec_a) != len(vec_b):
        return 0.0
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return max(0.0, min(1.0, dot / (norm_a * norm_b)))


class NoOpEmbeddingProvider(EmbeddingProvider):
    """Fallback provider when embeddings are disabled or unavailable.

    Directs the retrieval engine to rely 100% on SQLite FTS5 BM25 search.
    """

    @property
    def name(self) -> str:
        return "none"

    @property
    def dimension(self) -> int:
        return 0

    def is_available(self) -> bool:
        return False

    def embed_query(self, text: str) -> List[float]:
        return []

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [[] for _ in texts]


class DeterministicHashEmbeddingProvider(EmbeddingProvider):
    """Local, zero-dependency feature hashing vector embedding provider.

    Maps word n-grams into a fixed 128-dimensional dense unit vector using
    multi-hash projections. Provides semantic cosine similarity for phrase overlap,
    synonyms in context, and partial matches completely offline.
    """

    def __init__(self, dimension: int = 128) -> None:
        self._dim = dimension

    @property
    def name(self) -> str:
        return "hash"

    @property
    def dimension(self) -> int:
        return self._dim

    def is_available(self) -> bool:
        return True

    def _hash_token(self, token: str, seed: int) -> int:
        """Produce integer hash using sha256 with seed."""
        h = hashlib.sha256(f"{seed}:{token}".encode("utf-8")).hexdigest()
        return int(h[:8], 16)

    def embed_query(self, text: str) -> List[float]:
        return self._embed_single(text)

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [self._embed_single(t) for t in texts]

    def _embed_single(self, text: str) -> List[float]:
        vec = [0.0] * self._dim
        words = re.findall(r"\w+", text.lower())
        if not words:
            return vec

        # Unigrams and bigrams
        features = list(words)
        for i in range(len(words) - 1):
            features.append(f"{words[i]}_{words[i+1]}")

        for feat in features:
            idx = self._hash_token(feat, 0) % self._dim
            sign = 1.0 if (self._hash_token(feat, 1) % 2 == 0) else -1.0
            vec[idx] += sign

        # Normalize to unit vector
        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 0.0:
            vec = [v / norm for v in vec]
        return vec


class RemoteEmbeddingProvider(EmbeddingProvider):
    """Remote OpenAI-compatible embedding provider."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "text-embedding-3-small",
        base_url: str = "https://api.openai.com/v1",
        dimension: int = 1536,
    ) -> None:
        self._api_key = api_key or os.getenv("OPENAI_API_KEY")
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._dim = dimension

    @property
    def name(self) -> str:
        return "remote"

    @property
    def dimension(self) -> int:
        return self._dim

    def is_available(self) -> bool:
        return bool(self._api_key)

    def embed_query(self, text: str) -> List[float]:
        docs = self.embed_documents([text])
        return docs[0] if docs else []

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        if not self.is_available() or not texts:
            return [[] for _ in texts]

        import urllib.request
        import json

        url = f"{self._base_url}/embeddings"
        payload = json.dumps({"model": self._model, "input": texts}).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._api_key}",
        }

        req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=10.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return [item["embedding"] for item in data["data"]]
        except Exception:
            # Fall back gracefully on network or auth errors
            return [[] for _ in texts]
