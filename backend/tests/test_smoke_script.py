from scripts.ask import main
from tests.test_llm_generator import FakeClient


async def test_smoke_script_prints_sql_and_token_counts(capsys):
    await main("台北市有幾家咖啡店？", client=FakeClient(sql="SELECT COUNT(*) FROM cafes"), model_id="m", effort=None)

    out = capsys.readouterr().out
    assert "SELECT COUNT(*) FROM cafes" in out
    assert "input_tokens=321" in out
    assert "output_tokens=12" in out


async def test_smoke_script_prints_a_refusal_or_clarifying_question(capsys):
    client = FakeClient(kind="clarify", sql="", message="「最近」是指幾天內？")

    await main("最近熱門的店", client=client, model_id="m", effort=None)

    assert "[clarify] 「最近」是指幾天內？" in capsys.readouterr().out
