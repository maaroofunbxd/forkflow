"""forkflow: git helpers for forked service repos — refresh coworker remotes, borrow paths onto a branch from
upstream, open a pull request on the upstream repo after you push. Bash scripts in forkflow/git/; optional companion
to [gland](https://github.com/maaroofunbxd/gland) (`git sync` and the pre-push hook)."""

from pathlib import Path

__version__ = "0.1.0"

GIT_DIR = Path(__file__).resolve().parent / "git"
"""Installed bash scripts (forkflow-fetch, forkflow-borrow, forkflow-pr, primary.sh)."""
