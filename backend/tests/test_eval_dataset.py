"""The evaluation runs only against demo cafes (import-real-cafes D10): golden answers come from them."""

import pytest

from evaluation.dataset import NotDemoDataset, check_demo_dataset


class Db:
    def __init__(self, non_demo: int):
        self.non_demo = non_demo

    async def run(self, sql: str):
        return ["non_demo"], [[self.non_demo]]


async def test_demo_database_passes():
    await check_demo_dataset(Db(non_demo=0))


async def test_any_real_cafe_stops_the_evaluation():
    with pytest.raises(NotDemoDataset, match="812 cafes are not demo"):
        await check_demo_dataset(Db(non_demo=812))
