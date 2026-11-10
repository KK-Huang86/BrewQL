"""The demo check against the seeded demo database, as genbi_reader (import-real-cafes D10)."""

from evaluation.dataset import check_demo_dataset


async def test_seeded_demo_database_passes_the_check(executor):
    await check_demo_dataset(executor)
