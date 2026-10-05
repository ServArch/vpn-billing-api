from pydantic import BaseModel, Field


class SupportQueryRequest(BaseModel):
    query: str = Field(min_length=3, max_length=1000)
    top_k_rerank: int = Field(default=3, ge=1, le=10)


class ChunkCitation(BaseModel):
    title: str
    breadcrumbs: list[str]
    relevance_score: float
    snippet: str


class SupportQueryResponse(BaseModel):
    query: str
    direct_answer: str
    troubleshooting_steps: list[str]
    confidence: float
    detected_client: str | None = None
    relevant_protocol: str | None = None
    citations: list[ChunkCitation]
