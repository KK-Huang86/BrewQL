"""Run with: python3 -m unittest discover -s tools

db/checks/mutate.sh is exercised against a fake psql that records what it is sent, so these
tests need no database.
"""

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

MUTATE = Path(__file__).resolve().parents[1] / "db" / "checks" / "mutate.sh"
# mutate.sh echoes this between the mutation and the check; only an ERROR after it is the check's.
MARKER = "mutate.sh: mutation applied"

FAKE_PSQL = """#!/bin/sh
cat > "$RECORD"
printf '%s' "$FAKE_OUT"
exit "${FAKE_CODE:-0}"
"""


class MutateTest(unittest.TestCase):
    # Spec (harden-workflow-checks): mutate a story check inside a transaction that always rolls back.

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.psql = self.tmp / "psql"
        self.psql.write_text(FAKE_PSQL)
        self.psql.chmod(0o755)
        self.record = self.tmp / "sent.sql"
        self.check = self.tmp / "99_story.sql"
        self.check.write_text("DO $$ BEGIN RAISE EXCEPTION 'story broken'; END $$;\n")

    def tearDown(self):
        self._tmp.cleanup()

    def run_mutate(self, *args, out="", code=0):
        env = {**os.environ, "PSQL": str(self.psql), "RECORD": str(self.record),
               "FAKE_OUT": out, "FAKE_CODE": str(code)}
        return subprocess.run(["bash", str(MUTATE), *args], capture_output=True, text=True, env=env)

    def test_caught_mutation_prints_the_error_and_succeeds(self):
        result = self.run_mutate(
            "UPDATE cafes SET rating = 1", str(self.check),
            out=f"BEGIN\nUPDATE 200\n{MARKER}\nERROR:  story broken\nCONTEXT:  line 1\n", code=3,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stdout.strip(), "caught: ERROR:  story broken")

    def test_uncaught_mutation_fails(self):
        result = self.run_mutate("UPDATE cafes SET rating = 1", str(self.check), out=f"BEGIN\n{MARKER}\nDO\nROLLBACK\n")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout.strip(), "NOT caught")

    def test_mutation_runs_inside_a_transaction_that_rolls_back(self):
        self.run_mutate("DELETE FROM favorites", str(self.check), out=f"{MARKER}\nERROR:  story broken\n", code=3)
        sent = self.record.read_text()
        self.assertTrue(sent.lstrip().startswith("BEGIN;"), sent)
        self.assertTrue(sent.rstrip().endswith("ROLLBACK;"), sent)
        self.assertLess(sent.index("DELETE FROM favorites"), sent.index(MARKER))
        self.assertLess(sent.index(MARKER), sent.index("RAISE EXCEPTION"))

    def test_rollback_survives_a_check_ending_in_a_comment_without_newline(self):
        self.check.write_text("SELECT 1; -- last line, no newline")
        self.run_mutate("SELECT 1", str(self.check), out=f"{MARKER}\nERROR:  x\n", code=3)
        self.assertIn("\nROLLBACK;", self.record.read_text())

    def test_failed_mutation_is_not_reported_as_caught(self):
        # Review finding: a typo in the mutation raised ERROR before the check ran and read as caught.
        result = self.run_mutate("UPDATE cafes SET no_such_column = 1", str(self.check),
                                 out='BEGIN\nERROR:  column "no_such_column" does not exist\n', code=3)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertIn("no_such_column", result.stderr)

    def test_check_name_resolves_inside_db_checks(self):
        result = self.run_mutate("SELECT 1", "08_views_favorites.sql", out=f"{MARKER}\nERROR:  x\n", code=3)
        self.assertEqual(result.returncode, 0, result.stderr)
        story = (MUTATE.parent / "08_views_favorites.sql").read_text()
        self.assertIn(story.strip(), self.record.read_text())

    def test_psql_failure_without_a_check_error_is_not_a_verdict(self):
        # A refused connection must not read as "NOT caught" (or as caught).
        result = self.run_mutate("SELECT 1", str(self.check),
                                 out="psql: error: connection to server failed\n", code=2)
        self.assertEqual(result.returncode, 2)
        self.assertIn("connection to server failed", result.stderr)

    def test_missing_arguments_or_check_file_is_a_usage_error(self):
        for args in ([], ["SELECT 1"], ["SELECT 1", "no_such_check.sql"]):
            with self.subTest(args=args):
                result = self.run_mutate(*args)
                self.assertEqual(result.returncode, 2)
                self.assertIn("usage", result.stderr)
                self.assertFalse(self.record.exists(), "psql must not be called")


if __name__ == "__main__":
    unittest.main()
