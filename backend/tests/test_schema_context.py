from pathlib import Path

import sqlglot
from sqlglot import exp

from app.schema_context import SCHEMA_CONTEXT

SCHEMA_SQL = Path(__file__).parents[2] / "db" / "init" / "01_schema.sql"


def real_cafes_columns() -> set[str]:
    create = sqlglot.parse_one(SCHEMA_SQL.read_text(), read="postgres")
    return {col.name for col in create.find_all(exp.ColumnDef)}


def test_schema_context_describes_every_cafes_column():
    # Match the bullet "- <column>：" so "id" is not satisfied by "place_id".
    missing = {c for c in real_cafes_columns() if f"- {c}：" not in SCHEMA_CONTEXT}
    assert not missing, f"schema context is missing columns: {missing}"


def test_schema_context_lists_the_enum_values_the_model_must_use():
    for value in ("'yes'", "'maybe'", "'no'", "台北市", "新北市"):
        assert value in SCHEMA_CONTEXT


def test_prompt_tells_the_model_when_to_refuse_and_when_to_clarify():
    # The three cases from the spec: data changes, predictions, missing details.
    for phrase in ("kind", "refuse", "clarify", "修改", "預測", "時間範圍"):
        assert phrase in SCHEMA_CONTEXT, phrase


def test_prompt_forbids_disguising_a_refusal_as_an_empty_query():
    # Seen with real Bedrock in ticket 2: "SELECT 1 WHERE FALSE" instead of refusing.
    for trick in ("WHERE FALSE", "LIMIT 0"):
        assert trick in SCHEMA_CONTEXT, trick


def test_prediction_refusals_say_only_history_can_be_queried():
    # Spec scenario: refusing a forecast explains that only historical data exists.
    assert "只能查詢歷史資料" in SCHEMA_CONTEXT


def test_schema_context_describes_the_daily_activity_view():
    assert "v_daily_activity" in SCHEMA_CONTEXT
    for column in ("day", "searches", "new_users"):
        assert f"- {column}：" in SCHEMA_CONTEXT, column


def test_schema_context_explains_how_to_filter_searches_by_ticked_options():
    # filters is JSONB with only the ticked options; the model needs the keys and the operator.
    for text in ("no_time_limit", "has_socket", "pet_friendly", "filters @>"):
        assert text in SCHEMA_CONTEXT, text


def test_schema_context_defines_time_phrases():
    # "最近半年" alone must not trigger a clarifying question: it has a fixed meaning.
    for phrase in ("最近半年", "最近一個月", "最近一週"):
        assert phrase in SCHEMA_CONTEXT, phrase


def test_schema_context_defines_zero_result_rate_like_the_story_check():
    # Design D2 / db/checks/07: zero-result searches ÷ searches in the district.
    # numeric cast: integer division would turn every rate into 0.
    lines = [line for line in SCHEMA_CONTEXT.splitlines() if "搜尋落空率" in line]
    assert lines, "搜尋落空率 is not defined"
    definition = lines[0]
    for text in ("result_count = 0", "count(*)", "numeric", "district"):
        assert text in definition, text


def test_comparisons_return_one_category_and_one_measure():
    # Seen with real Bedrock in ticket 7: "哪些行政區最常搜尋不到結果？" came back with four
    # columns, so the page showed a table instead of a bar chart.
    for text in ("比較或排名", "一個類別欄", "一個主要指標", "除非問題要求"):
        assert text in SCHEMA_CONTEXT, text
