"""Prometheus metrics for real /api/ask traffic (observe-with-grafana D3, D4).

Only the API handler records here; the pipeline measures but never imports this module, so evals
and smoke scripts leave no trace on the dashboard. Every label value is a fixed enum or the
configured model ID: never question text, SQL or an IP address.
"""

from typing import Literal

from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram, generate_latest

from app.daily_limit import DailyQuestionLimit
from app.pipeline import AskResult
from app.pricing import guardrail_cost_usd, model_cost_usd

# Seconds; nginx gives up on the backend after 60.
BUCKETS = (0.1, 0.25, 0.5, 1, 2.5, 5, 10, 20, 30)
Unavailable = Literal["unavailable_guardrail", "unavailable_model", "unavailable_db"]


class AskMetrics:
    """One registry per app, so each test (and each app) counts on its own."""

    def __init__(self, daily_limit: DailyQuestionLimit | None = None) -> None:
        self.registry = CollectorRegistry()
        r = self.registry
        self.asks = Counter(
            "brewql_ask", "Answered questions by outcome", ["status", "refusal_source", "error_kind"], registry=r
        )
        self.ask_seconds = Histogram("brewql_ask_seconds", "Time to answer one question", buckets=BUCKETS, registry=r)
        self.stage_seconds = Histogram(
            "brewql_stage_seconds", "Time per call to each stage", ["stage"], buckets=BUCKETS, registry=r
        )
        self.tokens = Counter("brewql_llm_tokens", "Model tokens billed", ["model", "direction"], registry=r)
        self.guardrail_blocks = Counter(
            "brewql_guardrail_blocks", "Questions blocked by the input guardrail", ["reason"], registry=r
        )
        self.guardrail_units = Counter("brewql_guardrail_units", "Guardrail text units billed", ["policy"], registry=r)
        # Same prices as the eval (app/pricing.py); the dashboard never multiplies prices itself.
        self.cost = Counter("brewql_estimated_cost_usd", "Estimated Bedrock cost", ["component"], registry=r)
        self.unpriced = Counter(
            "brewql_unpriced_questions", "Questions whose cost is unknown, so the cost total is low", registry=r
        )
        self.daily_limit_hits = None
        if daily_limit is not None:
            # Read at scrape time, so the dashboard shows 0 right after Taipei midnight.
            Gauge("brewql_daily_questions_used", "Questions counted today", registry=r).set_function(
                daily_limit.used_today
            )
            Gauge("brewql_daily_question_limit", "Questions allowed per Taipei day", registry=r).set(daily_limit.limit)
            self.daily_limit_hits = Counter(
                "brewql_daily_limit_hits", "Questions refused by the daily limit", registry=r
            )

    def record(self, result: AskResult, seconds: float) -> None:
        usage = result.usage
        self.asks.labels(result.status, result.refusal_source or "", result.error_kind or "").inc()
        self.ask_seconds.observe(seconds)
        for timing in usage.stages:
            self.stage_seconds.labels(timing.stage).observe(timing.seconds)
        if usage.model_id:
            self.tokens.labels(usage.model_id, "input").inc(usage.input_tokens)
            self.tokens.labels(usage.model_id, "output").inc(usage.output_tokens)
        self.guardrail_units.labels("topic").inc(usage.guardrail.topic_units)
        self.guardrail_units.labels("content").inc(usage.guardrail.content_units)
        for reason in usage.guardrail_reasons:
            self.guardrail_blocks.labels(reason).inc()
        # Each part counts when known; a question with any unknown part is flagged, never guessed.
        model, guardrail = model_cost_usd(usage), guardrail_cost_usd(usage)
        if model is not None:
            self.cost.labels("model").inc(model)
        if guardrail is not None:
            self.cost.labels("guardrail").inc(guardrail)
        if model is None or guardrail is None:
            self.unpriced.inc()

    def record_unavailable(self, kind: Unavailable, seconds: float) -> None:
        """A 5xx: the pipeline raised, so only the outcome and total time are known."""
        self.asks.labels("error", "", kind).inc()
        self.ask_seconds.observe(seconds)

    def record_daily_limit_hit(self) -> None:
        if self.daily_limit_hits is not None:
            self.daily_limit_hits.inc()

    def render(self) -> bytes:
        return generate_latest(self.registry)
