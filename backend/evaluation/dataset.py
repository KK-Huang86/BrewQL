"""The evaluation's golden answers come from the demo cafes (import-real-cafes D10).

Checked before any paid call: on a real-mode database every reference answer would differ, and
the run would cost money to report nonsense.
"""

from app.pipeline import QueryExecutor

_COUNTS = """
SELECT count(*) AS total, count(*) FILTER (WHERE place_id NOT LIKE 'demo-%') AS non_demo FROM cafes
"""


class NotDemoDataset(Exception):
    pass


async def check_demo_dataset(db: QueryExecutor) -> None:
    _, [[total, non_demo]] = await db.run(_COUNTS)
    if total == 0:
        raise NotDemoDataset("no cafes: the database was not seeded; run the evaluation on the demo dataset")
    if non_demo:
        raise NotDemoDataset(
            f"{non_demo} cafes are not demo cafes: run the evaluation on the demo dataset (DATASET=demo)"
        )
