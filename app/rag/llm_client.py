import json
import re
from typing import Optional
import httpx
from pydantic import BaseModel, Field, ValidationError

from app.config import settings
from app.rag.retriever import RetrievedChunk


class SupportAnswerResponse(BaseModel):
    direct_answer: str = Field(description="Clear, concise direct answer to user question")
    troubleshooting_steps: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    detected_client: Optional[str] = None
    relevant_protocol: Optional[str] = None


class AsyncLLMClient:
    JSON_BLOCK_REGEX = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout: float = 30.0,
    ):
        self.base_url = (base_url or settings.LLM_API_BASE).rstrip("/")
        self.api_key = api_key or settings.LLM_API_KEY
        self.model = model or settings.LLM_MODEL
        self.timeout = timeout

    def _build_system_prompt(self) -> str:
        return (
            "You are a technical support assistant for a VPN service specializing in VLESS Reality, Xray, and Shadowsocks.\n"
            "Answer user questions accurately based ONLY on provided context documentation.\n"
            "Always return a valid JSON object matching this schema:\n"
            "{\n"
            '  "direct_answer": "string",\n'
            '  "troubleshooting_steps": ["step 1", "step 2"],\n'
            '  "confidence": 0.95,\n'
            '  "detected_client": "v2rayNG" | "Streisand" | "Shadowrocket" | null,\n'
            '  "relevant_protocol": "vless-reality" | null\n'
            "}"
        )

    def _build_user_prompt(self, query: str, context_chunks: list[RetrievedChunk]) -> str:
        context_parts = []
        for idx, item in enumerate(context_chunks, 1):
            context_parts.append(f"--- Doc Chunk #{idx} [{item.chunk.title}] ---\n{item.chunk.contextualized_text}")
        context_str = "\n\n".join(context_parts) if context_parts else "No relevant documentation found."

        return (
            f"User Question: {query}\n\n"
            f"Context Documentation:\n{context_str}\n\n"
            "Generate JSON response with direct_answer, troubleshooting_steps, confidence, detected_client, and relevant_protocol."
        )

    async def generate_support_answer(
        self,
        query: str,
        context_chunks: list[RetrievedChunk],
    ) -> SupportAnswerResponse:
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(query, context_chunks)

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                resp = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                )
                resp.raise_for_status()
                data = resp.json()
                raw_content = data["choices"][0]["message"]["content"]
            except httpx.HTTPError as exc:
                return SupportAnswerResponse(
                    direct_answer="Support service is temporarily unable to query LLM engine.",
                    troubleshooting_steps=["Please contact support agent directly or consult documentation."],
                    confidence=0.0,
                )

        return self._parse_and_validate(raw_content)

    def _parse_and_validate(self, text: str) -> SupportAnswerResponse:
        cleaned = text.strip()
        match = self.JSON_BLOCK_REGEX.search(cleaned)
        if match:
            cleaned = match.group(1)

        try:
            parsed = json.loads(cleaned)
            return SupportAnswerResponse.model_validate(parsed)
        except (json.JSONDecodeError, ValidationError):
            return SupportAnswerResponse(
                direct_answer=text[:400].strip(),
                troubleshooting_steps=[],
                confidence=0.5,
            )
