"""Run with: python3 -m unittest discover -s tools"""

import io
import unittest

from spec_check import check, main


class SpecCheckTest(unittest.TestCase):
    def test_code_change_without_spec_change_fails(self):
        ok, message = check(["backend/app/main.py"])
        self.assertFalse(ok)
        self.assertIn("backend/app/main.py", message)

    def test_code_change_with_spec_change_passes(self):
        ok, _ = check(["backend/app/main.py", "openspec/changes/ask-first-question/tasks.md"])
        self.assertTrue(ok)

    def test_changes_outside_code_dirs_pass(self):
        for paths in (["README.md"], [".github/workflows/backend.yml"], ["CLAUDE.md", "docs/notes.md"], []):
            with self.subTest(paths=paths):
                self.assertTrue(check(paths)[0])

    def test_lookalike_paths_are_not_code(self):
        # "backend-notes.md" is not under backend/; "openspec-old/" is not openspec/.
        self.assertTrue(check(["backend-notes.md"])[0])
        self.assertFalse(check(["db/init/01_schema.sql", "openspec-old/x.md"])[0])

    def test_blank_lines_and_whitespace_from_git_output_are_ignored(self):
        ok, message = check(["", "  backend/app/db.py  ", "\n"])
        self.assertFalse(ok)
        self.assertIn("backend/app/db.py", message)

    def test_main_reads_paths_from_stdin_and_sets_exit_code(self):
        self.assertEqual(main(io.StringIO("frontend/src/App.tsx\n")), 1)
        self.assertEqual(main(io.StringIO("frontend/src/App.tsx\nopenspec/specs/x/spec.md\n")), 0)


if __name__ == "__main__":
    unittest.main()
