from fastapi import APIRouter, HTTPException

from app.rag.retriever import TwoStageRetriever
from app.rag.llm_client import AsyncLLMClient
from app.schemas.support import SupportQueryRequest, SupportQueryResponse, ChunkCitation

router = APIRouter(prefix="/support", tags=["Support RAG"])

_retriever: TwoStageRetriever | None = None
_llm_client: AsyncLLMClient | None = None


def get_retriever() -> TwoStageRetriever:
    global _retriever
    if _retriever is None:
        _retriever = TwoStageRetriever()
    return _retriever


def get_llm_client() -> AsyncLLMClient:
    global _llm_client
    if _llm_client is None:
        _llm_client = AsyncLLMClient()
    return _llm_client


@router.post("/ask", response_model=SupportQueryResponse)
async def ask_support(payload: SupportQueryRequest):
    retriever = get_retriever()
    llm = get_llm_client()

    retrieved = retriever.retrieve(
        query=payload.query,
        top_k_rerank=payload.top_k_rerank,
    )

    llm_answer = await llm.generate_support_answer(
        query=payload.query,
        context_chunks=retrieved,
    )

    citations = [
        ChunkCitation(
            title=item.chunk.title,
            breadcrumbs=item.chunk.breadcrumbs,
            relevance_score=round(item.rerank_score, 4),
            snippet=item.chunk.content[:200] + ("..." if len(item.chunk.content) > 200 else ""),
        )
        for item in retrieved
    ]

    return SupportQueryResponse(
        query=payload.query,
        direct_answer=llm_answer.direct_answer,
        troubleshooting_steps=llm_answer.troubleshooting_steps,
        confidence=llm_answer.confidence,
        detected_client=llm_answer.detected_client,
        relevant_protocol=llm_answer.relevant_protocol,
        citations=citations,
    )
