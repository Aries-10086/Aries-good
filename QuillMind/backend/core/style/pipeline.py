from __future__ import annotations

from typing import Any, TypedDict

from .describe import describe_style
from .embedding import BaseEmbeddingProvider, embed_style_samples
from .features import extract_features
from .preprocess import preprocess_samples


class StyleExtractionResult(TypedDict):
    vector: list[float]
    features: dict[str, Any]
    description: str


def extract_style(
    samples: list[str],
    *,
    embedding_provider: BaseEmbeddingProvider | None = None,
) -> StyleExtractionResult:
    cleaned_samples = preprocess_samples(samples)

    if not cleaned_samples:
        raise ValueError("At least one non-empty writing sample is required.")

    features = extract_features(cleaned_samples)
    vector = embed_style_samples(cleaned_samples, provider=embedding_provider)
    description = describe_style(features)

    return {
        "vector": vector,
        "features": features,
        "description": description,
    }
