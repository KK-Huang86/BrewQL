"""CI structural check: a PR that changes code must also change something under openspec/.

Only checks *that* specs changed, not *whether* they match the code; that semantic
check is done by spectra verify/drift before opening a PR.
"""

import sys
from typing import TextIO

CODE_DIRS = ("backend/", "frontend/", "db/", "infra/")
SPEC_DIR = "openspec/"


def check(paths: list[str]) -> tuple[bool, str]:
    paths = [p.strip() for p in paths if p.strip()]
    code = [p for p in paths if p.startswith(CODE_DIRS)]
    spec = [p for p in paths if p.startswith(SPEC_DIR)]
    if code and not spec:
        listed = "\n".join(f"  - {p}" for p in code)
        return False, f"程式碼有變更，但 openspec/ 沒有對應的變更：\n{listed}"
    return True, "spec check passed"


def main(stdin: TextIO = sys.stdin) -> int:
    """Read changed paths (one per line, e.g. from `git diff --name-only`); return the exit code."""
    ok, message = check(stdin.read().splitlines())
    print(message)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
