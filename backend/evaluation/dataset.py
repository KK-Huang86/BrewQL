"""The evaluation's golden answers come from the demo cafes (import-real-cafes D10).

Checked before any paid call: on a real-mode database every reference answer would differ, and
the run would cost money to report nonsense.
"""

from typing import Any, Protocol

_NON_DEMO = "SELECT count(*) AS non_demo FROM cafes WHERE place_id NOT LIKE 'demo-%'"


class Database(Protocol):
    async def run(self, sql: str) -> tuple[list[str], list[list[Any]]]: ...


class NotDemoDataset(Exception):
    pass


async def check_demo_dataset(db: Database) -> None:
    _, [[non_demo]] = await db.run(_NON_DEMO)
    if non_demo:
        raise NotDemoDataset(
            f"{non_demo} cafes are not demo cafes: run the evaluation on the demo dataset (DATASET=demo)"
        )
