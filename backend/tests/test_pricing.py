"""One price table turns a question's usage into dollars, for evals now and metrics later."""

import pytest

from app.input_guard import GuardrailUsage
from app.pipeline import AskUsage
from app.pricing import MODEL_PRICES, cost_usd, guardrail_cost_usd, model_cost_usd

HAIKU_US = "us.anthropic.claude-haiku-4-5-20251001-v1:0"


def test_answered_question_costs_tokens_plus_both_guardrail_policies():
    usage = AskUsage(model_id=HAIKU_US, input_tokens=1100, output_tokens=50, guardrail=GuardrailUsage(1, 1))

    # 1100 x $1.10/M + 50 x $5.50/M + (1 + 1) x $0.15/1000
    assert cost_usd(usage) == pytest.approx(0.00121 + 0.000275 + 0.0003)


def test_blocked_question_costs_only_the_guardrail():
    usage = AskUsage(model_id=None, input_tokens=0, output_tokens=0, guardrail=GuardrailUsage(2, 2))

    assert cost_usd(usage) == pytest.approx(0.0006)


def test_unknown_model_cost_is_unknown_not_zero():
    # Reporting 0 would make a model look free; None makes the gap visible in the report.
    usage = AskUsage(model_id="anthropic.some-new-model", input_tokens=1000, output_tokens=10)

    assert cost_usd(usage) is None


def test_unreported_guardrail_usage_makes_cost_unknown():
    # Zero units would understate the bill; the report flags unknown cost as incomplete.
    usage = AskUsage(model_id=HAIKU_US, input_tokens=1000, output_tokens=10, guardrail=GuardrailUsage(reported=False))

    assert cost_usd(usage) is None


def test_nothing_used_costs_nothing():
    assert cost_usd(AskUsage()) == 0


def test_the_models_this_project_runs_are_priced():
    assert HAIKU_US in MODEL_PRICES
    assert "global.anthropic.claude-haiku-4-5-20251001-v1:0" in MODEL_PRICES


def test_model_and_guardrail_parts_are_priced_separately():
    # The dashboard splits cost by component, so each part must stand on its own.
    usage = AskUsage(model_id=HAIKU_US, input_tokens=1100, output_tokens=50, guardrail=GuardrailUsage(1, 1))

    assert model_cost_usd(usage) == pytest.approx(0.00121 + 0.000275)
    assert guardrail_cost_usd(usage) == pytest.approx(0.0003)


def test_a_question_that_never_reached_the_model_has_zero_model_cost():
    # Blocked by the guardrail: no model ID and no tokens is a known zero, not an unknown price.
    assert model_cost_usd(AskUsage(model_id=None, guardrail=GuardrailUsage(2, 2))) == 0


def test_an_unknown_part_does_not_hide_the_known_one():
    usage = AskUsage(
        model_id="anthropic.some-new-model", input_tokens=1000, output_tokens=10, guardrail=GuardrailUsage(1, 0)
    )

    assert model_cost_usd(usage) is None
    assert guardrail_cost_usd(usage) == pytest.approx(0.00015)
