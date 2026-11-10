"""Compare two evaluation reports (rag-knowledge-base: static vs rag).

    uv --directory backend run python -m evaluation.compare_runs evaluation/reports/A.json evaluation/reports/B.json

Reads the saved JSON reports; prints Markdown to paste into RESULTS.md.
"""

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class RunSide:
    mode: str
    started_at: str
    correct: int
    total: int
    avg_input_tokens: float | None
    avg_cost_usd: float | None
    p50_ms: int | None
    p95_ms: int | None


@dataclass(frozen=True)
class RunComparison:
    base: RunSide
    other: RunSide
    # difficulty -> ((base correct, total), (other correct, total))
    by_difficulty: dict[str, tuple[tuple[int, int], tuple[int, int]]]
    fixed: list[str]  # wrong in base, right in other
    broken: list[str]  # right in base, wrong in other
    sources: dict[str, list[str]]  # question id -> knowledge used by the other run (rag)


def compare_runs(base: dict[str, Any], other: dict[str, Any]) -> RunComparison:
    left = {q["id"]: q for q in base["questions"]}
    right = {q["id"]: q for q in other["questions"]}
    if left.keys() != right.keys():
        differ = sorted(left.keys() ^ right.keys())
        raise ValueError(f"runs cover different questions: {', '.join(differ)}")
    ids = list(left)
    by_difficulty = {
        d: (
            (score["correct"], score["total"]),
            (other["summary"]["by_difficulty"][d]["correct"], other["summary"]["by_difficulty"][d]["total"]),
        )
        for d, score in base["summary"]["by_difficulty"].items()
    }
    return RunComparison(
        base=_side(base),
        other=_side(other),
        by_difficulty=by_difficulty,
        fixed=[i for i in ids if not left[i]["correct"] and right[i]["correct"]],
        broken=[i for i in ids if left[i]["correct"] and not right[i]["correct"]],
        sources={i: right[i].get("sources") or [] for i in ids},
    )


def _side(report: dict[str, Any]) -> RunSide:
    s = report["summary"]
    return RunSide(
        mode=report["run"].get("prompt_mode", "static"),  # reports before rag had only static
        started_at=report["run"]["started_at"],
        correct=s["correct"],
        total=s["total"],
        avg_input_tokens=s["avg_input_tokens"],
        avg_cost_usd=s["avg_cost_usd"],
        p50_ms=s["p50_ms"],
        p95_ms=s["p95_ms"],
    )


def to_markdown(c: RunComparison) -> str:
    b, o = c.base, c.other
    lines = [
        f"# 評估比較：{b.mode} → {o.mode}",
        "",
        f"- 基準：{b.mode}（{b.started_at}）",
        f"- 比較：{o.mode}（{o.started_at}）",
        "",
        f"| 指標 | {b.mode} | {o.mode} |",
        "|---|---|---|",
        f"| 正確 | {b.correct}/{b.total} | {o.correct}/{o.total} |",
        *(f"| {d} | {bc}/{bt} | {oc}/{ot} |" for d, ((bc, bt), (oc, ot)) in c.by_difficulty.items()),
        f"| 每題平均輸入 token | {_num(b.avg_input_tokens)} | {_num(o.avg_input_tokens)} |",
        f"| 每題平均成本 | {_usd(b.avg_cost_usd)} | {_usd(o.avg_cost_usd)} |",
        f"| p50／p95 回應時間 | {_ms(b.p50_ms)}／{_ms(b.p95_ms)} | {_ms(o.p50_ms)}／{_ms(o.p95_ms)} |",
        "",
        f"- 從錯變對：{_ids(c.fixed)}",
        f"- 從對變錯：{_ids(c.broken)}",
    ]
    flipped = [i for i in c.fixed + c.broken if c.sources.get(i)]
    if flipped:
        lines += ["", f"## 翻轉題目在 {o.mode} 使用的知識", ""]
        lines += [f"- {i}：{', '.join(c.sources[i])}" for i in flipped]
    return "\n".join(lines) + "\n"


def _ids(ids: list[str]) -> str:
    return "、".join(ids) or "無"


def _num(value: float | None) -> str:
    return "—" if value is None else f"{value:.0f}"


def _usd(value: float | None) -> str:
    return "—" if value is None else f"${value:.5f}"


def _ms(value: int | None) -> str:
    return "—" if value is None else f"{value} ms"


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    base, other = (json.loads(Path(p).read_text(encoding="utf-8")) for p in argv)
    print(to_markdown(compare_runs(base, other)), end="")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
