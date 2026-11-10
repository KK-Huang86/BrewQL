"""The evaluation runs only against demo cafes (import-real-cafes D10): golden answers come from them."""

import pytest

from evaluation.dataset import NotDemoDataset, check_demo_dataset


class Db:
    def __init__(self, total: int, non_demo: int):
        self.total, self.non_demo = total, non_demo

    async def run(self, sql: str):
        return ["total", "non_demo"], [[self.total, self.non_demo]]


async def test_demo_database_passes():
    await check_demo_dataset(Db(total=200, non_demo=0))


async def test_any_real_cafe_stops_the_evaluation():
    with pytest.raises(NotDemoDataset, match="812 cafes are not demo"):
        await check_demo_dataset(Db(total=812, non_demo=812))


async def test_empty_database_stops_the_evaluation():
    # A real volume whose import failed has no cafes; it is not demo either.
    with pytest.raises(NotDemoDataset, match="no cafes"):
        await check_demo_dataset(Db(total=0, non_demo=0))
