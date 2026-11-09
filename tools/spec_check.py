"""CI structural checks on a PR's changed paths.

1. A PR that changes code must also change something under openspec/.
2. Each change the PR touches that already has specs/ must have a spec delta for every
   capability its proposal lists.
3. A PR that changes code touches at most one change under openspec/changes/ (the archive
   does not count); docs-only PRs may plan several.

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


def _is_code(path: str) -> bool:
    return path.strip().startswith(CODE_DIRS)


def check(paths: list[str]) -> tuple[bool, str]:
    paths = [p.strip() for p in paths if p.strip()]
    code = [p for p in paths if _is_code(p)]
    spec = [p for p in paths if p.startswith(SPEC_DIR)]
    if code and not spec:
        listed = "\n".join(f"  - {p}" for p in code)
        return False, f"程式碼有變更，但 openspec/ 沒有對應的變更：\n{listed}"
    return True, "spec check passed"


def mixed_changes(paths: list[str]) -> list[str]:
    """Changes a code PR touches, when there is more than one; otherwise empty."""
    if not any(_is_code(p) for p in paths):
        return []
    names = sorted(_touched_changes(paths))
    return names if len(names) > 1 else []


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
    for path in paths:
        path = path.strip()
        if not path.startswith(CHANGES_DIR):
            continue
        # "<name>/<file>"; a bare "openspec/changes/<name>" or the archive is not a change in progress.
        name, sep, _ = path[len(CHANGES_DIR) :].partition("/")
        if sep and name and name != "archive":
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
        print(f"{CHANGES_DIR}{name}: proposal 列出的 capability 沒有 spec delta：{', '.join(missing)}", file=out)
    mixed = mixed_changes(paths)
    if mixed:
        print(
            f"有程式碼變更的 PR 只能實作一個 change，這個 PR 動到：{', '.join(mixed)}；"
            "其他 change 的文件請移到另一個分支",
            file=out,
        )
    return 0 if ok and not gaps and not mixed else 1


if __name__ == "__main__":
    sys.exit(main())
