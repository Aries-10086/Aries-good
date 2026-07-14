from .describe import describe_style
from .embedding import (
    BaseEmbeddingProvider,
    EmbeddingError,
    OpenAIEmbeddingProvider,
    average_vectors,
    embed_style_samples,
)
from .features import extract_features
from .pipeline import StyleExtractionResult, extract_style
from .preprocess import preprocess_samples, preprocess_text
from .similarity import cosine_similarity


__all__ = (
    "BaseEmbeddingProvider",
    "EmbeddingError",
    "OpenAIEmbeddingProvider",
    "StyleExtractionResult",
    "average_vectors",
    "cosine_similarity",
    "describe_style",
    "embed_style_samples",
    "extract_features",
    "extract_style",
    "preprocess_samples",
    "preprocess_text",
)
