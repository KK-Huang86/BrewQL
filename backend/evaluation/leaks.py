"""Refuse a run whose rag examples contain a golden question (rag-knowledge-base: prevent leaks).

An example identical to a test question would hand the model the answer and inflate rag accuracy.
Only exact matches (ignoring spaces and the question mark) are automatic; close paraphrases are a
manual review, recorded in tasks.md.
"""

from app.knowledge import KnowledgeDoc
from evaluation.golden import GoldenQuestion


class ExampleLeak(ValueError):
    """A knowledge example repeats a golden question; the message names both."""


def check_leaks(golden: list[GoldenQuestion], knowledge: list[KnowledgeDoc]) -> None:
    questions = {_normalise(q.question): q.id for q in golden}
    for doc in knowledge:
        if doc.kind != "example":
            continue
        qid = questions.get(_normalise(doc.title))
        if qid is not None:
            raise ExampleLeak(f"{doc.id} repeats golden question {qid}; remove or reword the example")


def _normalise(text: str) -> str:
    return "".join(text.split()).rstrip("?？")
