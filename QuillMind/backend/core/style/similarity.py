from __future__ import annotations

import math


def cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    if not vec_a or not vec_b:
        raise ValueError("Vectors cannot be empty.")
    if len(vec_a) != len(vec_b):
        raise ValueError("Vectors must have the same dimension.")

    dot_product = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(value * value for value in vec_a))
    norm_b = math.sqrt(sum(value * value for value in vec_b))

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return max(-1.0, min(1.0, dot_product / (norm_a * norm_b)))
