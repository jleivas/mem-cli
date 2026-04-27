from __future__ import annotations

import logging
import math

_logger = logging.getLogger(__name__)
_MODEL_NAME = "all-MiniLM-L6-v2"
_model: object | None = None
_model_loaded: bool = False


def _load_model() -> object | None:
    global _model, _model_loaded
    if _model_loaded:
        return _model
    _model_loaded = True
    try:
        from sentence_transformers import SentenceTransformer  # type: ignore[import]
        _model = SentenceTransformer(_MODEL_NAME)
    except ImportError:
        _model = None
    except Exception:
        _logger.debug("Failed to load sentence-transformers model", exc_info=True)
        _model = None
    return _model


def is_available() -> bool:
    """Return True if sentence-transformers is installed."""
    try:
        import sentence_transformers  # noqa: F401  # type: ignore[import]
        return True
    except ImportError:
        return False


def embed(text: str) -> list[float] | None:
    """Return a unit-normalized embedding vector for *text*, or None if unavailable."""
    model = _load_model()
    if model is None:
        return None
    try:
        vector = model.encode(text)  # type: ignore[attr-defined]
        return vector.tolist()
    except Exception:
        _logger.debug("Embedding failed", exc_info=True)
        return None


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Return cosine similarity in [-1, 1] between two vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)
