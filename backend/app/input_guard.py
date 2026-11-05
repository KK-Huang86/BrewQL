"""Check each question with Amazon Bedrock Guardrails before the SQL model sees it."""

import asyncio
import logging
import time
from dataclasses import dataclass

log = logging.getLogger(__name__)

DEFAULT_BLOCK_MESSAGE = "這個問題無法處理：BrewQL 只回答 Find Coffee 咖啡店營運數據的問題。"


class InputGuardUnavailable(Exception):
    """The guardrail could not give a verdict; the question must not go on (fail closed)."""


@dataclass(frozen=True)
class GuardVerdict:
    blocked: bool
    message: str | None = None
    # Why it was blocked, e.g. ("prompt_attack",) or ("topic:off-topic",); for logs and evals.
    reasons: tuple[str, ...] = ()


class BedrockInputGuard:
    """ApplyGuardrail on the question alone, via an injected boto3 bedrock-runtime client."""

    def __init__(self, client, *, guardrail_id: str, guardrail_version: str):
        self._client = client
        self._guardrail_id = guardrail_id
        self._guardrail_version = guardrail_version

    async def check(self, question: str) -> GuardVerdict:
        start = time.perf_counter()
        try:
            # boto3 is synchronous; keep the event loop free.
            response = await asyncio.to_thread(
                self._client.apply_guardrail,
                guardrailIdentifier=self._guardrail_id,
                guardrailVersion=self._guardrail_version,
                source="INPUT",
                content=[{"text": {"text": question}}],
            )
            verdict = _verdict(response)
        except Exception as e:
            # Network, permission or an unreadable response: never treat as "passed".
            error = f"{type(e).__name__}: {e}"
            log.warning(
                "input guardrail failed error=%s latency_ms=%d", error, _ms(start), extra={"latency_ms": _ms(start)}
            )
            raise InputGuardUnavailable(error) from e
        # Outcome only; the question text belongs to the audit log, not here.
        log.info(
            "input guardrail blocked=%s reasons=%s latency_ms=%d",
            verdict.blocked,
            ",".join(verdict.reasons) or "-",
            _ms(start),
            extra={"blocked": verdict.blocked, "reasons": list(verdict.reasons), "latency_ms": _ms(start)},
        )
        return verdict


def _ms(start: float) -> int:
    return int((time.perf_counter() - start) * 1000)


def _verdict(response: dict) -> GuardVerdict:
    action = response["action"]
    if action == "NONE":
        return GuardVerdict(blocked=False)
    if action != "GUARDRAIL_INTERVENED":
        raise ValueError(f"unknown guardrail action: {action}")

    reasons: list[str] = []
    for assessment in response.get("assessments", []):
        for f in assessment.get("contentPolicy", {}).get("filters", []):
            if f.get("action") == "BLOCKED":
                reasons.append(f["type"].lower())
        for t in assessment.get("topicPolicy", {}).get("topics", []):
            if t.get("action") == "BLOCKED":
                reasons.append(f"topic:{t['name']}")
    message = next((o["text"] for o in response.get("outputs", []) if o.get("text")), DEFAULT_BLOCK_MESSAGE)
    return GuardVerdict(blocked=True, message=message, reasons=tuple(reasons))


def build_input_guard(*, aws_region: str, guardrail_id: str, guardrail_version: str) -> BedrockInputGuard:
    """Real client; no network call until the first question."""
    import boto3
    from botocore.config import Config

    # Short timeout, few retries: the model call still needs room under nginx's 60s.
    config = Config(connect_timeout=3, read_timeout=5, retries={"max_attempts": 2, "mode": "standard"})
    client = boto3.client("bedrock-runtime", region_name=aws_region, config=config)
    return BedrockInputGuard(client, guardrail_id=guardrail_id, guardrail_version=guardrail_version)
