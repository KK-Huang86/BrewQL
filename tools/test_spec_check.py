"""Run with: python3 -m unittest discover -s tools"""

import unittest

from spec_check import check


class SpecCheckTest(unittest.TestCase):
    def test_code_change_without_spec_change_fails(self):
        ok, message = check(["backend/app/main.py"])
        self.assertFalse(ok)
        self.assertIn("backend/app/main.py", message)

    def test_code_change_with_spec_change_passes(self):
        ok, _ = check(["backend/app/main.py", "openspec/changes/ask-first-question/tasks.md"])
        self.assertTrue(ok)


if __name__ == "__main__":
    unittest.main()
