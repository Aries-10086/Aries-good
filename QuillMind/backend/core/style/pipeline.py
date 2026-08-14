from __future__ import annotations

from typing import Any, TypedDict

from .describe import describe_style
from .embedding import BaseEmbeddingProvider, EmbeddingError, embed_style_samples
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
    existing_vector: list[float] | None = None,
    existing_sample_count: int = 0,
) -> StyleExtractionResult:
    cleaned_samples = preprocess_samples(samples)

    if not cleaned_samples:
        raise ValueError("At least one non-empty writing sample is required.")

    features = extract_features(cleaned_samples)
    provider = embedding_provider or OpenAIEmbeddingProvider()
    if (
        existing_vector
        and existing_sample_count > 0
        and len(cleaned_samples) > existing_sample_count
    ):
        from .embedding import merge_incremental_average

        new_samples = cleaned_samples[existing_sample_count:]
        new_vectors = provider.embed(new_samples)
        if len(new_vectors) != len(new_samples):
            raise EmbeddingError("Embedding provider returned an unexpected vector count.")
        vector = merge_incremental_average(
            existing_vector,
            existing_sample_count,
            new_vectors,
        )
    else:
        vector = embed_style_samples(cleaned_samples, provider=provider)
    description = describe_style(features)

    return {
        "vector": vector,
        "features": features,
        "description": description,
    }
