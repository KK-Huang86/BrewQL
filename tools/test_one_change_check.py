"""Run with: python3 -m unittest discover -s tools"""

import io
import unittest

from spec_check import main, mixed_changes


class OneChangePerCodePrTest(unittest.TestCase):
    # Spec (harden-workflow-checks): a PR that changes code implements exactly one change.

    def test_code_pr_touching_two_changes_lists_both(self):
        # What happened in ticket 7: planning docs for another change rode on a feature branch.
        paths = [
            "backend/app/charts.py",
            "openspec/changes/district-gap-bar-chart/tasks.md",
            "openspec/changes/import-real-cafes/proposal.md",
        ]
        self.assertEqual(mixed_changes(paths), ["district-gap-bar-chart", "import-real-cafes"])

    def test_docs_only_pr_may_plan_several_changes(self):
        paths = [
            "openspec/changes/import-real-cafes/proposal.md",
            "openspec/changes/import-open-data/proposal.md",
            "README.md",
        ]
        self.assertEqual(mixed_changes(paths), [])

    def test_archive_does_not_count_as_a_second_change(self):
        paths = [
            "db/init/02_seed.sql",
            "openspec/changes/view-favorite-insights/tasks.md",
            "openspec/changes/archive/2026-11-09-district-gap-bar-chart/tasks.md",
        ]
        self.assertEqual(mixed_changes(paths), [])

    def test_main_specs_do_not_count_as_a_change(self):
        paths = ["frontend/src/App.tsx", "openspec/changes/a/tasks.md", "openspec/specs/query-web-ui/spec.md"]
        self.assertEqual(mixed_changes(paths), [])

    def test_main_fails_and_names_the_changes(self):
        out = io.StringIO()
        code = main(
            io.StringIO("infra/terraform/main.tf\nopenspec/changes/a/tasks.md\nopenspec/changes/b/tasks.md\n"),
            out=out,
        )
        self.assertEqual(code, 1)
        self.assertIn("a, b", out.getvalue())


if __name__ == "__main__":
    unittest.main()
