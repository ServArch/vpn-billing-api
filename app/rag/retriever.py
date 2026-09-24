from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import numpy as np

from app.config import settings
from app.rag.chunker import HeaderAwareMarkdownChunker, MarkdownChunk


@dataclass
class RetrievedChunk:
    chunk: MarkdownChunk
    stage1_score: float
    rerank_score: float


class TwoStageRetriever:
    def __init__(
        self,
        embedding_model_name: Optional[str] = None,
        reranker_model_name: Optional[str] = None,
        knowledge_base_dir: Optional[Path | str] = None,
    ):
        self.embedding_model_name = embedding_model_name or settings.EMBEDDING_MODEL
        self.reranker_model_name = reranker_model_name or settings.RERANKER_MODEL
        self.knowledge_base_dir = Path(knowledge_base_dir or "knowledge_base")

        self._bi_encoder = None
        self._cross_encoder = None
        self._chunks: list[MarkdownChunk] = []
        self._chunk_embeddings: Optional[np.ndarray] = None
        self._initialized = False

    def _ensure_models_loaded(self):
        if self._bi_encoder is None:
            from sentence_transformers import SentenceTransformer
            self._bi_encoder = SentenceTransformer(self.embedding_model_name)

        if self._cross_encoder is None:
            from sentence_transformers import CrossEncoder
            self._cross_encoder = CrossEncoder(self.reranker_model_name)

    def load_and_index_documents(self):
        chunker = HeaderAwareMarkdownChunker()
        all_chunks: list[MarkdownChunk] = []

        if self.knowledge_base_dir.exists():
            for md_file in self.knowledge_base_dir.glob("**/*.md"):
                all_chunks.extend(chunker.chunk_file(md_file))

        self._chunks = all_chunks
        if not self._chunks:
            self._initialized = True
            return

        self._ensure_models_loaded()
        corpus_texts = [c.contextualized_text for c in self._chunks]
        embeddings = self._bi_encoder.encode(corpus_texts, convert_to_numpy=True, normalize_embeddings=True)
        self._chunk_embeddings = embeddings
        self._initialized = True

    def retrieve(
        self,
        query: str,
        top_k_candidates: int = 6,
        top_k_rerank: int = 3,
        min_score: float = 0.20,
    ) -> list[RetrievedChunk]:
        if not self._initialized:
            self.load_and_index_documents()

        if not self._chunks or self._chunk_embeddings is None:
            return []

        self._ensure_models_loaded()

        # Stage 1: Fast vector candidate retrieval via bi-encoder cosine similarity
        query_vec = self._bi_encoder.encode([query], convert_to_numpy=True, normalize_embeddings=True)[0]
        cosine_scores = np.dot(self._chunk_embeddings, query_vec)

        k_candidates = min(top_k_candidates, len(self._chunks))
        candidate_indices = np.argpartition(-cosine_scores, k_candidates - 1)[:k_candidates]
        candidate_indices = candidate_indices[np.argsort(-cosine_scores[candidate_indices])]

        candidates: list[tuple[MarkdownChunk, float]] = [
            (self._chunks[idx], float(cosine_scores[idx])) for idx in candidate_indices
        ]

        if not candidates:
            return []

        # Stage 2: Cross-Encoder full self-attention reranking for candidate filtering
        pairs = [[query, item[0].contextualized_text] for item in candidates]
        rerank_scores = self._cross_encoder.predict(pairs)

        results: list[RetrievedChunk] = []
        for (chunk, bi_score), cross_score in zip(candidates, rerank_scores):
            score = float(cross_score)
            if score >= min_score:
                results.append(
                    RetrievedChunk(
                        chunk=chunk,
                        stage1_score=bi_score,
                        rerank_score=score,
                    )
                )

        results.sort(key=lambda x: x.rerank_score, reverse=True)
        return results[:top_k_rerank]
