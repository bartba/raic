import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import numpy as np


class VectorStoreError(ValueError):
    pass


@dataclass(frozen=True)
class SearchResult:
    score: float
    metadata: Dict[str, Any]


class VectorStore:
    def __init__(
        self,
        vectors: np.ndarray,
        metadata: List[Dict[str, Any]],
        faiss_index: Optional[Any] = None,
    ):
        self.vectors = vectors
        self.metadata = metadata
        self.faiss_index = faiss_index
        self.dimension = int(vectors.shape[1])

    @classmethod
    def build(
        cls,
        embeddings: Sequence[Sequence[float]],
        metadata: Sequence[Dict[str, Any]],
        use_faiss: bool = True,
    ) -> "VectorStore":
        vectors = _normalize_embeddings(embeddings)
        if len(vectors) != len(metadata):
            raise VectorStoreError("embedding and metadata counts must match")

        metadata_list = [dict(item) for item in metadata]
        faiss_index = _build_faiss_index(vectors) if use_faiss else None
        return cls(vectors=vectors, metadata=metadata_list, faiss_index=faiss_index)

    @classmethod
    def load(cls, path: str, use_faiss: bool = True) -> "VectorStore":
        try:
            data = np.load(path, allow_pickle=False)
            vectors = data["vectors"].astype(np.float32)
            metadata_json = str(data["metadata_json"])
        except (OSError, KeyError, ValueError) as error:
            raise VectorStoreError("cannot load vector store: {0}".format(path)) from error

        try:
            metadata = json.loads(metadata_json)
        except json.JSONDecodeError as error:
            raise VectorStoreError("vector store metadata must be valid json") from error

        if not isinstance(metadata, list) or not all(
            isinstance(item, dict) for item in metadata
        ):
            raise VectorStoreError("vector store metadata must be a list of objects")

        if vectors.ndim != 2 or vectors.shape[0] != len(metadata):
            raise VectorStoreError("vector store vectors and metadata do not match")

        faiss_index = _build_faiss_index(vectors) if use_faiss else None
        return cls(vectors=vectors, metadata=metadata, faiss_index=faiss_index)

    def save(self, path: str) -> None:
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        metadata_json = json.dumps(self.metadata, ensure_ascii=False)
        np.savez_compressed(
            str(output_path),
            vectors=self.vectors.astype(np.float32),
            metadata_json=metadata_json,
        )

    def search(
        self,
        query_embedding: Sequence[float],
        top_k: int,
    ) -> List[SearchResult]:
        if top_k <= 0:
            raise VectorStoreError("top_k must be greater than 0")

        query = _normalize_query(query_embedding, self.dimension)
        limit = min(top_k, len(self.metadata))

        if self.faiss_index is not None:
            scores, indices = self.faiss_index.search(query.reshape(1, -1), limit)
            return self._results_from_indices(scores[0], indices[0])

        scores = self.vectors.dot(query)
        indices = np.argsort(-scores)[:limit]
        return self._results_from_indices(scores[indices], indices)

    def _results_from_indices(
        self,
        scores: Sequence[float],
        indices: Sequence[int],
    ) -> List[SearchResult]:
        results = []
        for score, index in zip(scores, indices):
            if index < 0:
                continue
            results.append(
                SearchResult(
                    score=_score_from_cosine(float(score)),
                    metadata=dict(self.metadata[int(index)]),
                )
            )
        return results


def _normalize_embeddings(embeddings: Sequence[Sequence[float]]) -> np.ndarray:
    vectors = np.asarray(embeddings, dtype=np.float32)
    if vectors.ndim != 2 or vectors.shape[0] == 0 or vectors.shape[1] == 0:
        raise VectorStoreError("embeddings must be a non-empty 2d array")

    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    if np.any(norms == 0):
        raise VectorStoreError("embedding vectors must not be zero")

    return vectors / norms


def _normalize_query(query_embedding: Sequence[float], dimension: int) -> np.ndarray:
    query = np.asarray(query_embedding, dtype=np.float32)
    if query.ndim != 1 or query.shape[0] != dimension:
        raise VectorStoreError("query embedding dimension mismatch")

    norm = np.linalg.norm(query)
    if norm == 0:
        raise VectorStoreError("query embedding must not be zero")

    return query / norm


def _build_faiss_index(vectors: np.ndarray) -> Optional[Any]:
    try:
        import faiss
    except ImportError:
        return None

    index = faiss.IndexFlatIP(vectors.shape[1])
    index.add(vectors.astype(np.float32))
    return index


def _score_from_cosine(score: float) -> float:
    return max(0.0, min(1.0, (score + 1.0) / 2.0))
