from __future__ import annotations

from abc import ABC, abstractmethod

from django.conf import settings


class EmbeddingError(Exception):
    """Raised when style embeddings cannot be generated."""


class BaseEmbeddingProvider(ABC):
    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError


class OpenAIEmbeddingProvider(BaseEmbeddingProvider):
    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.model = model or settings.STYLE_EMBEDDING_MODEL
        self._client = None

    @property
    def client(self):
        if not self.api_key:
            raise EmbeddingError("OPENAI_API_KEY is not configured.")

        if self._client is None:
            try:
                from openai import OpenAI
            except ImportError as exc:
                raise EmbeddingError("The openai package is not installed.") from exc

            self._client = OpenAI(
                api_key=self.api_key,
                timeout=settings.STYLE_EMBEDDING_TIMEOUT_SECONDS,
            )

        return self._client

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            raise ValueError("At least one text is required for embedding.")

        try:
            response = self.client.embeddings.create(model=self.model, input=texts)
        except Exception as exc:
            raise EmbeddingError("OpenAI embedding request failed.") from exc

        items = sorted(response.data, key=lambda item: item.index)
        return [[float(value) for value in item.embedding] for item in items]


def average_vectors(vectors: list[list[float]]) -> list[float]:
    if not vectors:
        raise ValueError("At least one vector is required.")

    dimension = len(vectors[0])
    if dimension == 0:
        raise ValueError("Embedding vectors cannot be empty.")
    if any(len(vector) != dimension for vector in vectors):
        raise ValueError("All embedding vectors must have the same dimension.")

    return [
        sum(vector[index] for vector in vectors) / len(vectors)
        for index in range(dimension)
    ]


def embed_style_samples(
    samples: list[str],
    *,
    provider: BaseEmbeddingProvider | None = None,
) -> list[float]:
    embedding_provider = provider or OpenAIEmbeddingProvider()
    vectors = embedding_provider.embed(samples)

    if len(vectors) != len(samples):
        raise EmbeddingError("Embedding provider returned an unexpected vector count.")

    return average_vectors(vectors)
