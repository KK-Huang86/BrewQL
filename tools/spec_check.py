"""CI structural checks on a PR's changed paths.

1. A PR that changes code must also change something under openspec/.
2. Each change the PR touches that already has specs/ must have a spec delta for every
   capability its proposal lists.

Only checks *that* specs exist, not *whether* they match the code; that semantic check
is done by spectra drift and code review before opening a PR.
"""

import re
import sys
from pathlib import Path
from typing import TextIO

CODE_DIRS = ("backend/", "frontend/", "db/", "infra/")
SPEC_DIR = "openspec/"
CHANGES_DIR = "openspec/changes/"
# "- `query-pipeline`: ..." under "## Capabilities".
CAPABILITY_BULLET = re.compile(r"^- `([a-z0-9-]+)`", re.MULTILINE)
# From "## Capabilities" to the next level-2 heading.
CAPABILITIES_SECTION = re.compile(r"^## Capabilities\n(.*?)(?=^## |\Z)", re.MULTILINE | re.DOTALL)
SKIP_SPECS = re.compile(r"^skip_specs:\s*true\s*$", re.MULTILINE)


def check(paths: list[str]) -> tuple[bool, str]:
    paths = [p.strip() for p in paths if p.strip()]
    code = [p for p in paths if p.startswith(CODE_DIRS)]
    spec = [p for p in paths if p.startswith(SPEC_DIR)]
    if code and not spec:
        listed = "\n".join(f"  - {p}" for p in code)
        return False, f"程式碼有變更，但 openspec/ 沒有對應的變更：\n{listed}"
    return True, "spec check passed"


def capability_gaps(paths: list[str], root: Path) -> dict[str, list[str]]:
    """Capabilities each touched change lists in its proposal but has no specs/<name>/spec.md for."""
    gaps = {}
    for name in sorted(_touched_changes(paths)):
        change = root / CHANGES_DIR / name
        # Deleted or not started yet (specs come when work begins), or explicitly spec-free.
        if not (change / "specs").is_dir() or _skips_specs(change):
            continue
        missing = [c for c in _listed_capabilities(change) if not (change / "specs" / c / "spec.md").is_file()]
        if missing:
            gaps[name] = missing
    return gaps


def _touched_changes(paths: list[str]) -> set[str]:
    names = set()
    for p in paths:
        p = p.strip()
        if p.startswith(CHANGES_DIR):
            name = p[len(CHANGES_DIR) :].split("/", 1)[0]
            if name and name != "archive" and "/" in p[len(CHANGES_DIR) :]:
                names.add(name)
    return names


def _skips_specs(change: Path) -> bool:
    meta = change / ".openspec.yaml"
    return meta.is_file() and SKIP_SPECS.search(meta.read_text(encoding="utf-8")) is not None


def _listed_capabilities(change: Path) -> list[str]:
    proposal = change / "proposal.md"
    if not proposal.is_file():
        return []
    section = CAPABILITIES_SECTION.search(proposal.read_text(encoding="utf-8"))
    return CAPABILITY_BULLET.findall(section.group(1)) if section else []


def main(stdin: TextIO = sys.stdin, *, root: Path = Path("."), out: TextIO = sys.stdout) -> int:
    """Read changed paths (one per line, e.g. from `git diff --name-only`); return the exit code."""
    paths = stdin.read().splitlines()
    ok, message = check(paths)
    print(message, file=out)
    gaps = capability_gaps(paths, root)
    for name, missing in gaps.items():
        print(f"openspec/changes/{name}: proposal 列出的 capability 沒有 spec delta：{', '.join(missing)}", file=out)
    return 0 if ok and not gaps else 1


if __name__ == "__main__":
    sys.exit(main())
