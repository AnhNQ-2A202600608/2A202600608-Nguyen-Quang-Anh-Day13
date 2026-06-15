from __future__ import annotations

import time
from dataclasses import dataclass

from . import metrics
from .incidents import STATE
from .mock_llm import FakeLLM
from .mock_rag import retrieve
from .pii import hash_user_id, summarize_text
from .tracing import langfuse_context, observe


@dataclass
class AgentResult:
    answer: str
    latency_ms: int
    tokens_in: int
    tokens_out: int
    cost_usd: float
    quality_score: float


class LabAgent:
    def __init__(self, model: str = "claude-sonnet-4-5") -> None:
        self.model = model
        self.llm = FakeLLM(model=model)

    @observe()
    def run(self, user_id: str, feature: str, session_id: str, message: str) -> AgentResult:
        started = time.perf_counter()
        docs = retrieve(message)
        prompt = f"Feature={feature}\nDocs={docs}\nQuestion={message}"
        
        # Dynamic Model Router for Cost Optimization
        # Simple queries (length < 30) are routed to a cheaper model 'claude-3-5-haiku'
        is_simple = len(message.strip()) < 30 and feature == "qa"
        routed_model = "claude-3-5-haiku" if is_simple else self.model
        
        from structlog.contextvars import bind_contextvars
        bind_contextvars(model=routed_model)
        
        llm = FakeLLM(model=routed_model)
        response = llm.generate(prompt)
        
        quality_score = self._heuristic_quality(message, response.text, docs)
        latency_ms = int((time.perf_counter() - started) * 1000)
        cost_usd = self._estimate_cost(response.usage.input_tokens, response.usage.output_tokens, routed_model)

        from structlog.contextvars import get_contextvars
        ctx = get_contextvars()
        correlation_id = ctx.get("correlation_id", "UNKNOWN")
        env = ctx.get("env", "dev")

        langfuse_context.update_current_trace(
            id=correlation_id,
            user_id=hash_user_id(user_id),
            session_id=session_id,
            tags=["lab", feature, routed_model, env],
            metadata={
                "correlation_id": correlation_id,
                "session_id": session_id,
                "user_id_hash": hash_user_id(user_id),
                "feature": feature,
                "model": routed_model,
                "env": env
            }
        )
        langfuse_context.update_current_observation(
            metadata={"doc_count": len(docs), "query_preview": summarize_text(message)},
            usage_details={"input": response.usage.input_tokens, "output": response.usage.output_tokens},
        )

        metrics.record_request(
            latency_ms=latency_ms,
            cost_usd=cost_usd,
            tokens_in=response.usage.input_tokens,
            tokens_out=response.usage.output_tokens,
            quality_score=quality_score,
        )

        return AgentResult(
            answer=response.text,
            latency_ms=latency_ms,
            tokens_in=response.usage.input_tokens,
            tokens_out=response.usage.output_tokens,
            cost_usd=cost_usd,
            quality_score=quality_score,
        )

    def _estimate_cost(self, tokens_in: int, tokens_out: int, model: str) -> float:
        if model == "claude-3-5-haiku":
            # Input: $0.25/M, Output: $1.25/M
            input_cost = (tokens_in / 1_000_000) * 0.25
            output_cost = (tokens_out / 1_000_000) * 1.25
        else:
            # Input: $3/M, Output: $15/M
            input_cost = (tokens_in / 1_000_000) * 3
            output_cost = (tokens_out / 1_000_000) * 15
        return round(input_cost + output_cost, 6)

    def _heuristic_quality(self, question: str, answer: str, docs: list[str]) -> float:
        score = 0.5
        if docs:
            score += 0.2
        if len(answer) > 40:
            score += 0.1
        if question.lower().split()[0:1] and any(token in answer.lower() for token in question.lower().split()[:3]):
            score += 0.1
        if "[REDACTED" in answer:
            score -= 0.2
        if STATE["low_quality"]:
            score -= 0.4
        return round(max(0.0, min(1.0, score)), 2)
