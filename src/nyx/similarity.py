"""Cosine similarity and vector math utilities."""

from __future__ import annotations

import math
from typing import List


def cosine_similarity(a: List[float], b: List[float]) -> float:
    """Compute cosine similarity between two vectors.

    Args:
        a: First vector.
        b: Second vector (must be same length as a).

    Returns:
        Cosine similarity in [0, 1] for non-negative vectors,
        or 0.0 if either vector has zero norm.
    """
    if len(a) != len(b) or not a:
        return 0.0

    dot = 0.0
    norm_a = 0.0
    norm_b = 0.0

    for i in range(len(a)):
        dot += a[i] * b[i]
        norm_a += a[i] * a[i]
        norm_b += b[i] * b[i]

    denom = math.sqrt(norm_a) * math.sqrt(norm_b)
    return dot / denom if denom > 0 else 0.0


def euclidean_distance(a: List[float], b: List[float]) -> float:
    """Compute Euclidean distance between two vectors."""
    if len(a) != len(b):
        return float("inf")
    return math.sqrt(sum((a[i] - b[i]) ** 2 for i in range(len(a))))
