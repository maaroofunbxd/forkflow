"""Console entry for forkflow: dispatch fetch, borrow, pr to bash scripts in forkflow/git/."""

from __future__ import annotations

import os
import shutil
import sys

from forkflow import GIT_DIR

_COMMANDS = frozenset(("fetch", "borrow", "pr"))
_USAGE = """usage: forkflow <command>
       forkflow fetch | borrow … | pr -t TITLE

Commands:
  fetch                 fetch upstream primary, origin, and every other remote
  borrow REMOTE/BRANCH PATH…   branch from upstream, checkout paths from a coworker
  pr -t TITLE           gh pr create on upstream (after push)

forkflow -h, forkflow --help, forkflow <command> -h"""


def _exec_bash(script: str, argv: list[str]) -> None:
    bash = shutil.which("bash")
    if not bash:
        sys.exit("forkflow: needs bash")
    path = GIT_DIR / script
    if not path.is_file():
        sys.exit(f"forkflow: missing {path}")
    os.execv(bash, [bash, str(path), *argv])


def git_dir() -> None:
    print(GIT_DIR)


def main() -> None:
    argv = sys.argv[1:]
    if not argv or argv[0] in ("-h", "--help"):
        print(_USAGE, file=sys.stderr)
        raise SystemExit(0 if argv and argv[0] in ("-h", "--help") else 2)
    if argv[0] in _COMMANDS and os.environ.get("_ARGCOMPLETE") != "1":
        _exec_bash(f"forkflow-{argv[0]}", argv[1:])
    print(f"forkflow: unknown command {argv[0]!r}\n\n{_USAGE}", file=sys.stderr)
    raise SystemExit(2)


if __name__ == "__main__":
    main()
