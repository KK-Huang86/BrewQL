"""Run with: python3 -m unittest discover -s tools"""

import io
import tempfile
import unittest
from pathlib import Path

from spec_check import capability_gaps, main

PROPOSAL = """## Why

x

## What Changes

- `not-a-capability`: a bullet outside the Capabilities section

## Capabilities

### New Capabilities

- `evaluation`: new

### Modified Capabilities

- `query-pipeline`: changed

## Impact

- `also-not-a-capability`
"""


class CapabilityGapsTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def change(self, name, *, proposal=PROPOSAL, specs=("evaluation", "query-pipeline"), skip_specs=False):
        d = self.root / "openspec" / "changes" / name
        d.mkdir(parents=True)
        (d / "proposal.md").write_text(proposal, encoding="utf-8")
        (d / ".openspec.yaml").write_text(
            "schema: spec-driven\n" + ("skip_specs: true\n" if skip_specs else ""), encoding="utf-8"
        )
        for cap in specs:
            (d / "specs" / cap).mkdir(parents=True)
            (d / "specs" / cap / "spec.md").write_text("## ADDED Requirements\n", encoding="utf-8")
        return f"openspec/changes/{name}/proposal.md"

    def test_listed_capability_without_a_spec_delta_is_a_gap(self):
        path = self.change("eval", specs=("evaluation",))

        self.assertEqual(capability_gaps([path], self.root), {"eval": ["query-pipeline"]})

    def test_every_listed_capability_with_a_delta_passes(self):
        self.assertEqual(capability_gaps([self.change("eval")], self.root), {})

    def test_only_bullets_under_capabilities_count(self):
        # Backticked bullets in What Changes or Impact are not capabilities.
        self.assertEqual(capability_gaps([self.change("eval")], self.root), {})

    def test_change_without_specs_yet_is_not_checked(self):
        # A ticket not started yet has only a proposal; its specs come when work begins.
        self.assertEqual(capability_gaps([self.change("later", specs=())], self.root), {})

    def test_skip_specs_change_is_not_checked(self):
        path = self.change("hygiene", specs=("evaluation",), skip_specs=True)

        self.assertEqual(capability_gaps([path], self.root), {})

    def test_change_the_pr_does_not_touch_is_not_checked(self):
        self.change("other", specs=("evaluation",))

        self.assertEqual(capability_gaps(["backend/app/main.py"], self.root), {})

    def test_archived_and_deleted_changes_are_skipped(self):
        paths = [
            "openspec/changes/archive/2026-11-08-eval/proposal.md",
            "openspec/changes/gone/proposal.md",
        ]

        self.assertEqual(capability_gaps(paths, self.root), {})

    def test_proposal_with_no_capabilities_passes(self):
        proposal = "## Capabilities\n\n### New Capabilities\n\n（無）\n\n## Impact\n"

        self.assertEqual(capability_gaps([self.change("docs", proposal=proposal, specs=("x",))], self.root), {})

    def test_each_touched_change_is_reported_once(self):
        path = self.change("eval", specs=("evaluation",))
        tasks = "openspec/changes/eval/tasks.md"

        self.assertEqual(capability_gaps([path, tasks], self.root), {"eval": ["query-pipeline"]})

    def test_main_fails_and_names_the_missing_capability(self):
        path = self.change("eval", specs=("evaluation",))
        out = io.StringIO()

        code = main(io.StringIO(f"backend/app/x.py\n{path}\n"), root=self.root, out=out)

        self.assertEqual(code, 1)
        self.assertIn("eval", out.getvalue())
        self.assertIn("query-pipeline", out.getvalue())


if __name__ == "__main__":
    unittest.main()
