"""Bedrock price table: one place for what a question costs, shared by evals and metrics.

Prices are USD, on-demand, us-east-1, checked 2026-11-08:
- Guardrails: AWS Bedrock pricing page (https://aws.amazon.com/bedrock/pricing/), $0.15 per 1,000
  text units for content filters and for denied topics, the same for the standard and classic tiers.
- Claude Haiku 4.5: the AWS page shows no per-token figures, so the rates come from public price
  trackers (e.g. futureagi.com, verified 2026-10-22). Geo profiles such as us.* cost 10% more than
  global. Reconcile against Cost Explorer (observe-with-grafana) before trusting them for budgets.
- Titan Text Embeddings V2: $0.02 per million input tokens, from AWS's launch post
  (https://aws.amazon.com/blogs/machine-learning/get-started-with-amazon-titan-text-embeddings-v2-a-new-state-of-the-art-embeddings-model-on-amazon-bedrock/),
  checked 2026-11-10; some trackers list $0.20, ten times the AWS figure, and are not used.
Change prices here only.
"""

from dataclasses import dataclass

from app.pipeline import AskUsage


@dataclass(frozen=True)
class ModelPrice:
    input_per_mtok: float
    output_per_mtok: float


MODEL_PRICES: dict[str, ModelPrice] = {
    "us.anthropic.claude-haiku-4-5-20251001-v1:0": ModelPrice(input_per_mtok=1.10, output_per_mtok=5.50),
    "global.anthropic.claude-haiku-4-5-20251001-v1:0": ModelPrice(input_per_mtok=1.00, output_per_mtok=5.00),
    "anthropic.claude-haiku-4-5-20251001-v1:0": ModelPrice(input_per_mtok=1.00, output_per_mtok=5.00),
}

# Embedding models: USD per million input tokens (rag-knowledge-base D9).
EMBEDDING_PRICES_PER_MTOK: dict[str, float] = {
    "amazon.titan-embed-text-v2:0": 0.02,
}

# Per 1,000 text units (1 unit = up to 1,000 characters); each policy is billed separately.
GUARDRAIL_TOPIC_PER_1K_UNITS = 0.15
GUARDRAIL_CONTENT_PER_1K_UNITS = 0.15


def guardrail_cost_usd(usage: AskUsage) -> float | None:
    """Guardrail dollars, or None when the response carried no units (unknown, not zero)."""
    if not usage.guardrail.reported:
        return None
    return (
        usage.guardrail.topic_units * GUARDRAIL_TOPIC_PER_1K_UNITS
        + usage.guardrail.content_units * GUARDRAIL_CONTENT_PER_1K_UNITS
    ) / 1000


def model_cost_usd(usage: AskUsage) -> float | None:
    """Model dollars, or None when tokens were billed by a model missing from the table."""
    if usage.input_tokens == 0 and usage.output_tokens == 0:
        return 0.0
    price = MODEL_PRICES.get(usage.model_id or "")
    if price is None:
        return None
    return (usage.input_tokens * price.input_per_mtok + usage.output_tokens * price.output_per_mtok) / 1_000_000


def embedding_cost_usd(usage: AskUsage) -> float | None:
    """Embedding dollars (rag mode), 0 without one, or None when the embedding model is not in the table."""
    if usage.embedding_tokens == 0:
        return 0.0
    price = EMBEDDING_PRICES_PER_MTOK.get(usage.embedding_model_id or "")
    if price is None:
        return None
    return usage.embedding_tokens * price / 1_000_000


def cost_usd(usage: AskUsage) -> float | None:
    """Dollars for one question, or None when a model is missing from the table or guardrail units are unknown."""
    parts = (guardrail_cost_usd(usage), model_cost_usd(usage), embedding_cost_usd(usage))
    if any(part is None for part in parts):
        return None
    return sum(parts)
