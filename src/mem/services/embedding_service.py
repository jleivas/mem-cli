from __future__ import annotations

import math
import re

# Fixed vector size. 256 buckets is enough for short memory snippets and
# keeps stored embeddings small. Uses feature hashing (the "hashing trick")
# so no vocabulary file is needed.
_DIMS = 256


def _stable_hash(s: str) -> int:
    """Deterministic djb2 hash — unaffected by PYTHONHASHSEED."""
    h = 5381
    for byte in s.encode():
        h = ((h << 5) + h + byte) & 0xFFFFFFFF
    return h


def _tokenize(text: str) -> list[str]:
    """Return words + character bigrams for partial/fuzzy matching.

    Example: "authentication" produces tokens ["authentication"] plus bigrams
    ["au", "ut", "th", ...], so a query "auth" shares bigrams with it and
    scores higher than an unrelated word.
    """
    words = re.findall(r"[a-z0-9]+", text.lower())
    bigrams = [word[i : i + 2] for word in words for i in range(len(word) - 1)]
    return words + bigrams


def embed(text: str) -> list[float] | None:
    """Return a normalized TF vector for *text* using feature hashing."""
    tokens = _tokenize(text)
    if not tokens:
        return None

    counts: dict[int, float] = {}
    for token in tokens:
        idx = _stable_hash(token) % _DIMS
        counts[idx] = counts.get(idx, 0.0) + 1.0

    vec = [counts.get(i, 0.0) for i in range(_DIMS)]
    norm = math.sqrt(sum(x * x for x in vec))
    if norm == 0.0:
        return None
    return [x / norm for x in vec]


def is_available() -> bool:
    return True


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if len(a) != len(b):
        # Dimension mismatch: old sentence_transformers embeddings (384-dim)
        # vs new TF vectors (256-dim). Treat as no similarity so they sort
        # to the end and get re-embedded naturally on next save.
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)
